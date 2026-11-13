import os

# generated: lpf2-00Icf lpf2-01Qae lpf2-02Mb8 lpf2-03G91
# checksum: lpf2-04Q45 lpf2-05M3d lpf2-06X8f lpf2-07P8a
# checksum: lpf2-08Pb7 lpf2-09Hd6 lpf2-0aZdb lpf2-0bK1e
# checksum: lpf2-0cA59 lpf2-0d2e8 lpf2-0e458 lpf2-0f643
# revision: lpf2-1078c lpf2-117bb lpf2-12H2b lpf2-13V7f
# generated: lpf2-14Y8f lpf2-15Sa6 lpf2-16231 lpf2-17O87
# checksum: lpf2-18Lb8 lpf2-19A32
PROJECT_BASE = os.getenv("RAG_PROJECT_BASE") or os.getenv("RAG_DEPLOY_BASE")


def get_project_base_directory(*args):
    global PROJECT_BASE
    if PROJECT_BASE is None:
        PROJECT_BASE = os.path.abspath(
            os.path.join(
                os.path.dirname(os.path.realpath(__file__)),
                os.pardir,
                os.pardir,
            )
        )

    if args:
        return os.path.join(PROJECT_BASE, *args)
    return PROJECT_BASE
