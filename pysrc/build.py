# -*- coding: utf-8 -*-

import os
import random
import string
import subprocess
import apkrepack
import optparse

import sys

sdkbuild = os.path.abspath(os.path.join(os.path.split(os.path.realpath(sys.argv[0]))[0], "../build.bat"))
if "repacktool" in sdkbuild:
    sdkbuild = r'E:\Project\AD_SO_SDK_PACKAGE\build.bat'
sdk_dir = os.path.join(os.path.dirname(sdkbuild), "sdk-jar", "release")
gpAPK_dir = os.path.join(os.path.dirname(sdkbuild), "gpapk")


def buildSdk(pkgname, cid, f=True):
    out_name = pkgname

    out_name += ("_%s__pie.apk" % cid)
    sdkapkdir = os.path.abspath(os.path.join(sdk_dir, out_name))
    if f or not os.path.exists(sdkapkdir):
        p = subprocess.Popen("%s %s %s" % (sdkbuild, pkgname, cid), shell=True, stderr=subprocess.PIPE)
        stdout, stderr = p.communicate()
        retcode = p.wait()
        if not retcode == 0:
            raise Exception("build sdk failed!" + stderr)

    return sdkapkdir, pkgname


def getgpApk():
    for root, dirs, files in os.walk(gpAPK_dir):
        for file in files:
            if '.apk' in file:
                return os.path.join(root, file)
    return ''


def main():
    parser = optparse.OptionParser(usage='usage: %prog cid [-t <apkPath>]', version='%prog 1.0')
    parser.add_option('-t', '--target', dest='apkPath', type='string', metavar='FILE',
                      help='specify target apk [default: %default]')
    parser.add_option('-p', "--packagename", dest='pkgname', type='string', default='',
                      help="default random package name for sdk")
    parser.add_option('-r', "--replace", dest='re_pkgname', type='string', default='',
                      help="replace target apk package name")
    parser.add_option('-g', "--gppckage", dest='gp', action='store_true')

    options, args = parser.parse_args()
    print(args)
    cid = len(args) > 0 and args[0] or ""

    gp = False
    if options.gp:
        gp = True

    onlybuildsdk = False
    target = None
    if not options.apkPath:
        print("[+] just build sdk!")
        onlybuildsdk = True
    else:
        target = options.apkPath

    if options.pkgname:
        pkgname = options.pkgname
    else:
        pkgname = ramdonPackName()

    targetPackageName = ""
    if options.re_pkgname:
        targetPackageName = options.re_pkgname

    print(pkgname)

    print(os.path.split(os.path.abspath(sys.argv[0]))[0])

    if cid and target:
        pkgname = targetPackageName and targetPackageName or apkrepack.getAppBaseInfo(target)[0]

    print("[*] " + "cid: " + cid + " pkgname: " + pkgname)
    if gp:
        cid = ""
    apk_dir, packageName = buildSdk(pkgname, cid)
    if not onlybuildsdk:
        keystore_dir = os.path.join(os.path.dirname(sdkbuild), "Everychange.key")
        apkrepack.process(apk_dir, target, packageName, keystore_dir, targetPackageName, getgpApk(), gp)


def ramdonPackName():
    pkgname = 'com'
    l = random.randint(2, 3)
    for i in range(l):
        pkgname += '.' + ranString(4, 5)
    return pkgname


def ranString(s, t):
    return ''.join(random.sample(string.ascii_lowercase, random.randint(s, t)))


if __name__ == '__main__':
    main()
    # apkrepack.process(r'E:\PycharmProjects\repacktool\com.bxdw.omzw___pie.apk', r'E:\PycharmProjects\repacktool\app-release.apk' , '', '', '', r'E:\Project\AD_SO_SDK_PACKAGE\gpapk\IMEI_Show.apk')
    # for root, dirs, files in os.walk(r'E:\Project\AD_SO_SDK_PACKAGE\gpapk'):
    #    for file in files:
    #        if not '.apk' in file:
    #            continue
    #        print(file.decode('gb2312').encode('utf-8'))
    #        print(os.path.join(root, file))
