#!/usr/bin/python
# -*- coding: <utf-8> -*-
import os, re, sys, glob
from optparse import OptionParser
import xml.etree.cElementTree as ET

ADDONSXMLHEADER = '<?xml version="1.0" encoding="UTF-8"?>\n<addons>'
ADDONSXMLFOOTER = '</addons>\n'
DEFAULTDESCNAME = 'addon.xml'

def getDescPaths(path):
    """crawls path for addon.xml files, then returns a list of them"""
    descPaths = list()
    for item in os.listdir(path):
        if os.path.isfile(os.path.join(path, item, DEFAULTDESCNAME)):
            descPaths.append(os.path.join(path, item, DEFAULTDESCNAME))
    descPaths.sort(key=lambda p: os.stat(p).st_mtime, reverse=True)
    return descPaths

def get_xml_from_file(path):
    elem = ET.parse(path).getroot()
    for subelement in elem:
        if subelement.tag == "extension" and (subelement.attrib["point"] == "xbmc.addon.metadata" or subelement.attrib["point"] == "kodi.addon.metadata"):
            if not os.path.exists(os.path.join(os.path.dirname(path),'icon.png')):
                noicon = ET.SubElement(subelement,'noicon')
                noicon.text = "true"
            if not os.path.exists(os.path.join(os.path.dirname(path),'fanart.jpg')):
                nofanart = ET.SubElement(subelement,'nofanart')
                nofanart.text = "true"
            if not glob.glob(os.path.join(os.path.dirname(path),'changelog*.txt')):
                nochangelog = ET.SubElement(subelement,'nochangelog')
                nochangelog.text = "true"
    return ET.tostring(elem,encoding='utf-8')

def remove_xml_header(xml):
    return re.sub('.*<\?xml.+?\>', '', xml, 1)

def write_xml(xml_string, xml_dest):
    if (xml_dest != ""):
        try:
             f = open(xml_dest, 'w')
             f.write(xml_string)
             f.close()
        except:
            print "Unexpected error:", sys.exc_info()[0]
            raise
    else:
            sys.stdout.write(xml_string)

if __name__ == '__main__':
    addonsxml = str()
    parser = OptionParser()
    parser.add_option('-p', '--addons-path', dest='addons_path', default='.')
    parser.add_option('-d', '--dest', dest='dest', default='')
    (options, args) = parser.parse_args()
    
    for addon_path in getDescPaths(options.addons_path):
        addon = get_xml_from_file(addon_path)
        addon = remove_xml_header(addon)
        addonsxml = addonsxml + addon
    addonsxml = ADDONSXMLHEADER + addonsxml + ADDONSXMLFOOTER
    write_xml(addonsxml, options.dest)
