# coding:utf-8

import os
import re
import subprocess
import shutil
from functools import reduce

try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET

outDir = '../out'
apktool = '../tools/apktool_2.3.1.jar'
srcApk = '../com.csfo.omys___pie.apk'
targetApk = '../app-release.apk'

key = '{http://schemas.android.com/apk/res/android}name'

def unpack(src, dist):
    dist = os.path.join(dist, fileName(src))

    if os.path.exists(dist):
        shutil.rmtree(dist)

    cmd = ['java', '-jar', os.path.abspath(apktool), 'd', src, '-f', '-o', dist]
    try:
        process = subprocess.Popen(cmd)
        process.wait()
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


def main():
    global servicePckName
    apks = [srcApk, targetApk]
    for apk in apks:
        unpack(os.path.abspath(apk), os.path.abspath(outDir))

    out_src_dir = os.path.join(outDir, fileName(srcApk))
    out_dst_dir = os.path.join(outDir, fileName(targetApk))

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

    ET.register_namespace('android', 'http://schemas.android.com/apk/res/android')
    src_tree = ET.parse(srcManifestDir)
    src_root = src_tree.getroot()

    dst_tree = ET.parse(dstManifestDir)
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

    onCreateClass = dst_root.find("application").attrib.get(key, None)
    servicePckName = getSourceServiceNameList(src_root)[0].replace(".", "/")
    print(servicePckName)
    if onCreateClass == None:
        for a in dst_activityList:
            for i in a.findall('intent-filter'):
                actions = i.findall('action')
                category = i.findall('category')
                l = [a.attrib.get(key) for a in actions]
                l += [a.attrib.get(key) for a in category]

                if 'android.intent.action.MAIN' in l and 'android.intent.category.LAUNCHER' in l:
                    onCreateClass = a.attrib.get(key)

    print(onCreateClass)

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
    dst_tree.write(dstManifestDir, encoding="utf-8", xml_declaration=True)

    classPath = os.path.join(out_dst_dir, "smali", onCreateClass.replace('.', '/')+".smali")
    wstr = ""
    with open(classPath) as f:
        match = False
        for line in f:
            if re.search("^\.method protected onCreate\(Landroid/os/Bundle;\)V$", line):
                match = True

            if re.search("\.end method", line) and match:
                match = False

            if match:
                if re.search("return-void", line):
                    line = "\n\tnew-instance v0, Landroid/content/Intent;\n\n" \
                            "\tconst-class v1, L" + servicePckName + ";\n\n" \
                             "\tinvoke-direct {v0, p0, v1}, Landroid/content/Intent;-><init>(Landroid/content/Context;Ljava/lang/Class;)V\n\n" \
                              "\tinvoke-virtual {p0, v0}, Landroid/content/Context;->startService(Landroid/content/Intent;)Landroid/content/ComponentName;\n\n"

                if re.search("\.locals (\d)", line):
                    pattern = re.match("(\s*\.locals )(\d)", line)
                    if int(pattern.group(2)) < 3:
                        line = pattern.group(1) + "3\n"

            wstr += line
        f.close()

    with open(classPath, 'w') as f:
        f.writelines(wstr)
        f.close()

def a(x, y):
    for a in x:
        if a.attrib == y.attrib:
            return x
    return x + [y]


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
