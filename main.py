# -*- coding: utf-8 -*-
__author__ = 'dontsov'

import os
import fnmatch
from random import randint
import xml.etree.ElementTree as ET
from xml.dom import minidom

from datetime import datetime, timedelta
import uuid
import argparse


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
    for root, dir, files in os.walk(dir_path):
        for slide in fnmatch.filter(files, "*.jpg"):
            slides.append((os.path.splitext(slide)[0], os.path.join(dir_path, slide)))

    return slides


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


if __name__ == "__main__":
    #parser = argparse.ArgumentParser(description='Arduino to web data converter')
    #parser.add_argument('keyfile', nargs='?', default='debug.txt')
    #parser.add_argument('idir', nargs='?', default='Pictures')
    #parser.add_argument('ofile', nargs='?', default='test.fcpxml')
    #parser.add_argument('-u', '--url', default='http://127.0.0.1:45000/data', help='URL to send data')
    #args = parser.parse_args()
    #
    # вход
    # файл кейлоггера
    # папка с фото
    #
    # выход
    # файл проекта finalcut 1.4

    keylogger_file = 'debug.txt'
    final_cut_ofile = 'test.fcpxml'
    dir_path = os.path.join(os.getcwd(), "Pictures")

    slide0_duration_msec = 1000
    slideLast_duration_msec = 1000

    # [timestamp]
    timestamps = parse_keylogger_file(keylogger_file, slide0_duration_msec, slideLast_duration_msec)

    # [(file_name, file_path)]
    slides = parse_slide_folder(dir_path)

    gap_duration_msec = 40
    frames_per_second = 25   # 25 | 30
    fc_library_location = "file:///Users/dontsov/Movies/keylogger.fcpbundle/"
    fc_event_name = "20.03.17"
    fc_project_name = "keylogger_proj"

    # Размер видео
    width = '1920'
    height = '1080'

    # Размер слайдов
    widthFFVideoFormatRateUndefined = '2999'
    heightFFVideoFormatRateUndefined = '2248'


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
                                              'height': height})

    # Формат слайдов импортированных
    ET.SubElement(resources, 'format', attrib={'id': 'r2',
                                              'name': 'FFVideoFormatRateUndefined',
                                              'width': widthFFVideoFormatRateUndefined,
                                              'height': heightFFVideoFormatRateUndefined})

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

    slide_index, offset, duration, name, path, id = data[-1]
    full_duration = offset + duration + gap_duration_msec
    sequence = ET.SubElement(project, 'sequence', attrib={'duration': fc_duration(full_duration, frames_per_second),
                                              'format': 'r1',
                                              'tcStart': '0s',
                                              'tcFormat': 'NDF',
                                              'audioLayout': 'stereo',
                                              'audioRate': '48k'})
    spine = ET.SubElement(sequence, 'spine')

    ET.SubElement(spine, 'gap', attrib={'name': 'Gap',
                                        'offset': '0s',
                                        'duration': fc_duration(gap_duration_msec, frames_per_second),
                                        'start': '3600s'})

    #add gap to data
    for d in data:
        slide_index, offset, duration, name, path, id = d
        ET.SubElement(spine, 'video', attrib={'name': name,
                                    'offset': fc_duration(offset + gap_duration_msec, frames_per_second),
                                    'ref': id,
                                    'duration': fc_duration(duration, frames_per_second),
                                    'start': '3600s'})

    with open(final_cut_ofile, 'w') as f:
        # original header:
        # f.write('<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n<!DOCTYPE fcpxml>\n')
        # can't write "standalone="no"", but works

        dom = minidom.parseString(ET.tostring(fcpxml, encoding="utf-8"))

        dt = minidom.getDOMImplementation('').createDocumentType('fcpxml', '', '')

        dom.insertBefore(dt, dom.documentElement)

        dom.version = '1.0'
        f.write(dom.toprettyxml(indent='\t', encoding='utf-8'))