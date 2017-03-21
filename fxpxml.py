# -*- coding: utf-8 -*-
__author__ = 'dontsov'

import os
import fnmatch
from random import randint
import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime
import uuid

from image import get_image_size


def parse_keylogger_buf(lines, slide0_duration_msec, slideLast_duration_msec):
    '''
    :param file_path: файл с нажатыми клавишами вида
    2017-03-18 04:00:00.983\t[Down]
    :return:   slide index, offset in millisec, duration in millisec
    '''
    time_mask = '%Y-%m-%d %H:%M:%S.%f'

    timestamps = [(0, 0, slide0_duration_msec)] # первый слайд не понятно сколько был на экране

    start_time = datetime.strptime(lines[0].split('\t')[0], time_mask)

    current_slide = 1

    prev_duraion = slide0_duration_msec
    prev_timestamp = start_time
    for line in lines[1:]:
        ts, key = line.split('\t')
        timestamp = datetime.strptime(ts, time_mask)

        duration = (timestamp - prev_timestamp).total_seconds()*1000.0

        offset_msec = (prev_timestamp - start_time).total_seconds()*1000.0 \
                      + slide0_duration_msec

        prev_timestamp = timestamp
        if 'Up' in key:
            timestamps.append((current_slide, offset_msec, duration))
            current_slide -= 1
        elif 'Down' in key:
            timestamps.append((current_slide, offset_msec, duration))
            current_slide += 1

    #last
    offset_msec = (prev_timestamp - start_time).total_seconds()*1000.0 \
                  + slide0_duration_msec
    timestamps.append((current_slide, offset_msec, slideLast_duration_msec))

    return timestamps


def parse_keylogger_file(file_path, slide0_duration_msec, slideLast_duration_msec):
    with open(file_path, 'r') as f:
        lines = f.readlines()
    return parse_keylogger_buf(lines, slide0_duration_msec, slideLast_duration_msec)


def parse_slide_folder(dir_path):
    '''
    :param dir_path:
    :return:  [(file name, file path)]
    '''
    slides = []
    width = 0
    height = 0
    for root, dir, files in os.walk(dir_path):
        for slide in fnmatch.filter(files, "*.jpg"):
            slides.append((os.path.splitext(slide)[0], os.path.join(dir_path, slide)))
            if not width:
                width, height = get_image_size(os.path.join(dir_path, slide))

    return slides, width, height


def gen_uid():
    ret = ''
    for i in range(0,8):
        ret = ret + '%02x' % randint(0, 100000)
    return ret.upper()


def fc_duration(msec, frames_per_sec):
    if msec == 0:
        return '0s'
    t = msec * frames_per_sec / 10
    t = int(round(t / 100.0) * 100)

    if t % (frames_per_sec * 100) == 0:
        return str(t / (frames_per_sec * 100)) + 's'
    return str(t) + '/' + str(frames_per_sec * 100) + 's'


def write_xml(data, output_path):

    with open(output_path, 'w') as f:
        # original header:
        # f.write('<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n<!DOCTYPE fcpxml>\n')
        # can't write "standalone="no"", but works

        dom = minidom.parseString(ET.tostring(data, encoding="utf-8"))
        dt = minidom.getDOMImplementation('').createDocumentType('fcpxml', '', '')

        dom.insertBefore(dt, dom.documentElement)

        dom.version = '1.0'
        f.write(dom.toprettyxml(indent='\t', encoding='utf-8'))

        print 'FinalCut project file: {0}'.format(output_path)


def generator(*args, **kwargs):

    keylog_path = kwargs.get('keylog')
    slides_dir = kwargs.get('slides')
    output_path = kwargs.get('output')

    gap_duration_msec = kwargs.get('gap_sec') * 1000
    slide0_duration_msec = kwargs.get('first_sec') * 1000
    slideLast_duration_msec = kwargs.get('last_sec') * 1000

    frames_per_second = kwargs.get('frames') # 25 | 30

    fc_library_location = "file:///Users/dontsov/Movies/keylogger.fcpbundle/"
    fc_event_name = kwargs.get('event')
    fc_project_name = kwargs.get('name')

    # Размер видео
    width = str(kwargs.get('width'))
    height = str(kwargs.get('height'))

   # [timestamp]
    timestamps = parse_keylogger_file(keylog_path, slide0_duration_msec, slideLast_duration_msec)

    # Список слайдов и их размер
    # [(file_name, file_path)], width, height
    slides, widthFFVideoFormatRateUndefined, heightFFVideoFormatRateUndefined = parse_slide_folder(slides_dir)

    # [(slide_index, offset, duration, name, path, id)]
    data = []
    for timestamp in timestamps:
        slide, offset, duration = timestamp
        if len(slides) > slide:
            name, path = slides[slide]
            rX = 'r' + str(slide + 3)
            data.append((slide, offset, duration, name, path, rX))


    fcpxml = ET.Element('fcpxml', attrib={'version': '1.4'})
    resources = ET.SubElement(fcpxml, 'resources')

    ET.SubElement(resources, 'format', attrib={'id': 'r1',
                                              'name': 'FFVideoFormat1080p' + str(frames_per_second),
                                              'frameDuration': fc_duration(1000/frames_per_second, frames_per_second),
                                              'width': width,
                                              'height': height
    })

    # Формат слайдов импортированных
    ET.SubElement(resources, 'format', attrib={'id': 'r2',
                                              'name': 'FFVideoFormatRateUndefined',
                                              'width': str(widthFFVideoFormatRateUndefined),
                                              'height': str(heightFFVideoFormatRateUndefined)
    })

    resource_added = []
    for d in data:
        slide_index, offset, duration, name, path, id = d

        if id not in resource_added: # we should print only unique files
            asset = ET.SubElement(resources, 'asset', attrib={ 'id': id,
                                                      'name': name,
                                                      'uid': gen_uid(),
                                                      'src': 'file://' + path,
                                                      'start': '0s',
                                                      'duration': '0s',
                                                      'hasVideo': '1',
                                                      'format': 'r2'
            })
            metadata = ET.SubElement(asset, 'metadata')
            ET.SubElement(metadata, 'md', attrib={'key': 'com.apple.proapps.mio.ingestDate',
                                                       'value': '2017-03-20 02:17:23 +0300'})
            ET.SubElement(metadata, 'md', attrib={'key': 'com.apple.proapps.spotlight.kMDItemOrientation',
                                                       'value': '0'})

            resource_added.append(id)

    library = ET.SubElement(fcpxml, 'library', attrib={'location': fc_library_location})
    event = ET.SubElement(library, 'event', attrib={'name': fc_event_name, 'uid': str(uuid.uuid4())})
    project = ET.SubElement(event, 'project', attrib={'name': fc_project_name, 'uid': str(uuid.uuid4())})

    if not data:
        print 'No slides found'
    else:
        slide_index, offset, duration, name, path, id = data[-1]
        full_duration = offset + duration + gap_duration_msec
        sequence = ET.SubElement(project, 'sequence', attrib={'duration': fc_duration(full_duration, frames_per_second),
                                                  'format': 'r1',
                                                  'tcStart': '0s',
                                                  'tcFormat': 'NDF',
                                                  'audioLayout': 'stereo',
                                                  'audioRate': '48k'})
        spine = ET.SubElement(sequence, 'spine')

        if gap_duration_msec:
            ET.SubElement(spine, 'gap', attrib={'name': 'Gap',
                                                'offset': '0s',
                                                'duration': fc_duration(gap_duration_msec, frames_per_second),
                                                'start': '3600s'})

        # add gap to data
        for d in data:
            slide_index, offset, duration, name, path, id = d
            ET.SubElement(spine, 'video', attrib={'name': name,
                                        'offset': fc_duration(offset + gap_duration_msec, frames_per_second),
                                        'ref': id,
                                        'duration': fc_duration(duration, frames_per_second),
                                        'start': '3600s'})

        write_xml(fcpxml, output_path)