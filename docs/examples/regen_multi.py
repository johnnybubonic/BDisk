#!/usr/bin/env python3.6

import copy
from lxml import etree

with open('single_profile.xml', 'rb') as f:
    xml = etree.fromstring(f.read())

single_profile = xml.xpath('/bdisk/profile[1]')[0]
alt_profile = copy.deepcopy(single_profile)
for c in alt_profile.xpath('//comment()'):
    p = c.getparent()
    p.remove(c)

# Change the profile identifiers
alt_profile.attrib['name'] = 'alternate'
alt_profile.attrib['id'] = '2'
alt_profile.attrib['uuid'] = '2ed07c19-2071-4d66-8569-da40475ba716'

meta_tags = {'name': 'AnotherCD',
             'uxname': 'bdisk_alt',
             'pname': '{xpath_ref%../name/text()}',
             'desc': 'Another rescue/restore live environment.',
             'author': 'Another Dev Eloper',
             'email': '{xpath_ref%//profile[@name="default"]/meta/dev/email/text()}',
             'website': '{xpath_ref%//profile[@name="default"]/meta/dev/website/text()}',
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
        e.attrib['hashed'] = 'no'
    elif e.tag == 'user':
        e.attrib['sudo'] = 'no'
# Delete the second user
accounts.remove(accounts[2])
xml.append(alt_profile)

with open('multi_profile.xml', 'wb') as f:
    f.write(etree.tostring(xml,
                           pretty_print = True,
                           encoding = 'UTF-8',
                           xml_declaration = True))
