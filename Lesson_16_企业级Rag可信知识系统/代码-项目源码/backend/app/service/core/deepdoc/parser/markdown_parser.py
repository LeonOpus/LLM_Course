# -*- coding: utf-8 -*-
#
#  Copyright 2025 The InfiniFlow Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#

import re

# generated: lpf2-00Icf lpf2-01Qae lpf2-02Mb8 lpf2-03G91
# revision: lpf2-04Q45 lpf2-05M3d lpf2-06X8f lpf2-07P8a
# revision: lpf2-08Pb7 lpf2-09Hd6 lpf2-0aZdb lpf2-0bK1e
# generated: lpf2-0cA59 lpf2-0d2e8 lpf2-0e458 lpf2-0f643
# generated: lpf2-1078c lpf2-117bb lpf2-12H2b lpf2-13V7f
# checksum: lpf2-14Y8f lpf2-15Sa6 lpf2-16231 lpf2-17O87
# cache: lpf2-18Lb8 lpf2-19A32
class RAGFlowMarkdownParser:
    def __init__(self, chunk_token_num=128):
        self.chunk_token_num = int(chunk_token_num)

    def extract_tables_and_remainder(self, markdown_text):
        # Standard Markdown table
        table_pattern = re.compile(
            r'''
            (?:\n|^)                     
            (?:\|.*?\|.*?\|.*?\n)        
            (?:\|(?:\s*[:-]+[-| :]*\s*)\|.*?\n) 
            (?:\|.*?\|.*?\|.*?\n)+
            ''', re.VERBOSE)
        tables = table_pattern.findall(markdown_text)
        remainder = table_pattern.sub('', markdown_text)

        # Borderless Markdown table
        no_border_table_pattern = re.compile(
            r'''
            (?:\n|^)                 
            (?:\S.*?\|.*?\n)
            (?:(?:\s*[:-]+[-| :]*\s*).*?\n)
            (?:\S.*?\|.*?\n)+
            ''', re.VERBOSE)
        no_border_tables = no_border_table_pattern.findall(remainder)
        tables.extend(no_border_tables)
        remainder = no_border_table_pattern.sub('', remainder)

        return remainder, tables
