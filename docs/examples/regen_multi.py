#!/usr/bin/env python3.6

import copy
from lxml import etree, objectify

#parser = etree.XMLParser(remove_blank_text = True)
parser = etree.XMLParser(remove_blank_text = False)

# We need to append to a new root because you can't edit nsmap, and you can't
# xpath on an element with a naked namespace (e.g. 'xlmns="..."').
ns = {None: 'http://bdisk.square-r00t.net/',
      'xsi': 'http://www.w3.org/2001/XMLSchema-instance'}
xsi = {'{http://www.w3.org/2001/XMLSchema-instance}schemaLocation':
           'http://bdisk.square-r00t.net bdisk.xsd'}
new_cfg = etree.Element('bdisk', nsmap = ns, attrib = xsi)
new_cfg.text = '\n    '

with open('single_profile.xml', 'rb') as f:
    xml = etree.fromstring(f.read(), parser)


roottree = xml.getroottree()
for elem in roottree.getiterator():
    if not hasattr(elem.tag, 'find'):
        continue
    i = elem.tag.find('}')
    if i >= 0:
        elem.tag = elem.tag[i + 1:]
objectify.deannotate(roottree, cleanup_namespaces = True)


single_profile = xml.xpath('/bdisk/profile[1]')[0]
alt_profile = copy.deepcopy(single_profile)
for c in alt_profile.xpath('//comment()'):
    p = c.getparent()
    p.remove(c)

# Change the profile identifiers
alt_profile.attrib['name'] = 'alternate'
alt_profile.attrib['id'] = '2'
alt_profile.attrib['uuid'] = '2ed07c19-2071-4d66-8569-da40475ba716'

meta_tags = {'name': 'ALTCD',
             'uxname': 'bdisk_alt',
             'pname': '{xpath%../name/text()}',
             'desc': 'Another rescue/restore live environment.',
             'author': 'Another Dev Eloper',
             'email': '{xpath%//profile[@name="default"]/meta/dev/email/text()}',
             'website': '{xpath%//profile[@name="default"]/meta/dev/website/text()}',
             'ver': '0.0.1'}
# Change the names
meta = alt_profile.xpath('/profile/meta')[0]
for e in meta.iter():
    if e.tag in meta_tags:
        e.text = meta_tags[e.tag]

accounts_tags = {'rootpass': 'atotallyinsecurepassword',
                 'username': 'testuser',
                 'comment': 'Test User',
                 'password': 'atestpassword'}
accounts = alt_profile.xpath('/profile/accounts')[0]
for e in accounts.iter():
    if e.tag in accounts_tags:
        e.text = accounts_tags[e.tag]
    if e.tag == 'rootpass':
        e.attrib['hashed'] = 'false'
    elif e.tag == 'user':
        e.attrib['sudo'] = 'false'
# Delete the second user
accounts.remove(accounts[2])
author = alt_profile.xpath('/profile/meta/dev/author')[0]
author.addnext(etree.Comment(
    ' You can reference other profiles within the same configuration. '))
#xml.append(alt_profile)

for child in xml.xpath('/bdisk/profile'):
    new_cfg.append(copy.deepcopy(child))
new_cfg.append(alt_profile)

with open('multi_profile.xml', 'wb') as f:
    f.write(etree.tostring(new_cfg,
                           pretty_print = True,
                           encoding = 'UTF-8',
                           xml_declaration = True))
