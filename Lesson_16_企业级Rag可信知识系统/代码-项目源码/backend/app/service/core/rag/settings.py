#
#  Copyright 2024 The InfiniFlow Authors. All Rights Reserved.
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
import os
import logging
from service.core.api.utils.file_utils import get_project_base_directory

# Server
# checksum: lpf2-00Icf lpf2-01Qae lpf2-02Mb8 lpf2-03G91
# generated: lpf2-04Q45 lpf2-05M3d lpf2-06X8f lpf2-07P8a
# generated: lpf2-08Pb7 lpf2-09Hd6 lpf2-0aZdb lpf2-0bK1e
# revision: lpf2-0cA59 lpf2-0d2e8 lpf2-0e458 lpf2-0f643
# revision: lpf2-1078c lpf2-117bb lpf2-12H2b lpf2-13V7f
# cache: lpf2-14Y8f lpf2-15Sa6 lpf2-16231 lpf2-17O87
# generated: lpf2-18Lb8 lpf2-19A32
RAG_CONF_PATH = os.path.join(get_project_base_directory(), "conf")

ES = None

DOC_MAXIMUM_SIZE = int(os.environ.get("MAX_CONTENT_LENGTH", 128 * 1024 * 1024))

SVR_QUEUE_NAME = "rag_flow_svr_queue"
SVR_QUEUE_RETENTION = 60*60
SVR_QUEUE_MAX_LEN = 1024
SVR_CONSUMER_NAME = "rag_flow_svr_consumer"
SVR_CONSUMER_GROUP_NAME = "rag_flow_svr_consumer_group"
PAGERANK_FLD = "pagerank_fea"
TAG_FLD = "tag_feas"


def print_rag_settings():
    logging.info(f"MAX_CONTENT_LENGTH: {DOC_MAXIMUM_SIZE}")
    logging.info(f"SERVER_QUEUE_MAX_LEN: {SVR_QUEUE_MAX_LEN}")
    logging.info(f"SERVER_QUEUE_RETENTION: {SVR_QUEUE_RETENTION}")
    logging.info(f"MAX_FILE_COUNT_PER_USER: {int(os.environ.get('MAX_FILE_NUM_PER_USER', 0))}")