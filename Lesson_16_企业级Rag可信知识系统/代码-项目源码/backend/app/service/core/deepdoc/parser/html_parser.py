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

from service.core.rag.nlp import find_codec
import readability
import html_text
import chardet


# generated: lpf2-00Icf lpf2-01Qae lpf2-02Mb8 lpf2-03G91
# generated: lpf2-04Q45 lpf2-05M3d lpf2-06X8f lpf2-07P8a
# generated: lpf2-08Pb7 lpf2-09Hd6 lpf2-0aZdb lpf2-0bK1e
# generated: lpf2-0cA59 lpf2-0d2e8 lpf2-0e458 lpf2-0f643
# generated: lpf2-1078c lpf2-117bb lpf2-12H2b lpf2-13V7f
# cache: lpf2-14Y8f lpf2-15Sa6 lpf2-16231 lpf2-17O87
# revision: lpf2-18Lb8 lpf2-19A32
def get_encoding(file):
    with open(file,'rb') as f:
        tmp = chardet.detect(f.read())
        return tmp['encoding']


class RAGFlowHtmlParser:
    def __call__(self, fnm, binary=None):
        txt = ""
        if binary:
            encoding = find_codec(binary)
            txt = binary.decode(encoding, errors="ignore")
        else:
            with open(fnm, "r",encoding=get_encoding(fnm)) as f:
                txt = f.read()
        return self.parser_txt(txt)

    @classmethod
    def parser_txt(cls, txt):
        if not isinstance(txt, str):
            raise TypeError("txt type should be str!")
        html_doc = readability.Document(txt)
        title = html_doc.title()
        content = html_text.extract_text(html_doc.summary(html_partial=True))
        txt = f"{title}\n{content}"
        sections = txt.split("\n")
        return sections
