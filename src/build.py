# coding:utf-8

import os
import subprocess
import apkrepack

sdkbuild = r'E:\Project\AD_SO_SDK_PACKAGE\build.bat'
sdk_dir = os.path.join(os.path.dirname(sdkbuild), "sdk-jar", "release")


def buildSdk(pkgname, cid="12223"):
    p = subprocess.Popen("%s %s %s" % (sdkbuild, pkgname, cid), shell=True)
    retcode = p.wait()
    if not retcode == 0:
        raise Exception("build sdk failed!")

    apkname = pkgname
    if cid:
        pkgname += "_"+cid
    pkgname += "___pie.apk"
    return os.path.abspath(os.path.join(sdk_dir, pkgname)), apkname


def main():
    apk_dir, packageName = buildSdk("com.xa.coa")
    keystore_dir = os.path.join(os.path.dirname(sdkbuild), "Everychange.key")
    print("[+] " + keystore_dir)
    apkrepack.process(apk_dir, r"C:\Users\Administrator\Desktop\Battery-Indicator-Pro-release.apk", packageName, keystore_dir)

if __name__ == '__main__':
    main()
