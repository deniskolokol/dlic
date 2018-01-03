import requests
from .app import settings
from .fileutils import cwd
from unipath import Path, FSPath


def get_local_file_name(key):
    local_file = key.strip('/').replace('/', '_')
    return settings.DMWORKER_WORKING_DIR.child(local_file)


def download_file(url, local_file):
    # NOTE the stream=True parameter
    r = requests.get(url, stream=True)
    with open(local_file, 'wb') as f:
        for chunk in r.iter_content(chunk_size=1024):
            if chunk:
                f.write(chunk)
                f.flush()
    return local_file


def download_from_api_server(api_file):
    local_file = '_'.join(api_file.split('/')[3:])
    local_file = settings.DMWORKER_WORKING_DIR.child(local_file)
    download_file(api_file, local_file)
    return local_file


def clean_working_dir(exclude=None, working_dir=settings.DMWORKER_WORKING_DIR):
    exclude = exclude if exclude is not None else []
    if not isinstance(exclude, list):
        raise ValueError('Exclude should be list')
    with cwd(working_dir):
        exclude = [Path(ex).absolute() for ex in exclude]
        f1 = lambda x: x not in exclude and x.isfile()
        f2 = lambda x: not any(ex.startswith(x) for ex in exclude)
        for p in FSPath(working_dir).walk(filter=f1):
            p.remove()
        for p in list(FSPath(working_dir).walk(filter=f2)):
            p.rmtree()
