import re
import os
from contextlib import contextmanager
import datetime as dt
import anyjson as json
from itertools import chain
from collections import Counter
from .datafile import S3File
from .app import settings, log
from .exception import (InvalidDataFile, InvalidCSV, DmException,
                        InvalidTimeseries, InternalException)
from .fileutils import (open_file, open_gz, open_bz, TempFile,
                        Archive, md5, InvalidArchive, ProcessCall)
from .helpers import (get_local_file_name, clean_working_dir,
                      download_from_api_server)


RE_FLOAT = r'[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?'
FORMAT_ERROR = "The dataset is empty or isn't properly formatted."
notify = None


def set_notify(_notify):
    global notify
    notify = _notify


@contextmanager
def global_notify(_notify):
    global notify
    notify = _notify
    yield
    notify = None


def run(key, _notify=None, api_file=None):
    def _clean_working_dir(exclude=None):
        exclude = exclude if exclude is not None else []
        try:
            clean_working_dir(exclude=exclude)
        except (IOError, OSError):
            msg = 'Can\'t clean working directory'
            log.error(msg)
            notify.admin_send(msg)

    def get_local_file():
        if remote_file.exists():
            source = 's3'
            local_file = get_local_file_name(remote_file.key)
            if local_file.exists() and md5(local_file) == remote_file.etag():
                _clean_working_dir([local_file])
            else:
                _clean_working_dir()
                remote_file.download(local_file)
        elif api_file is not None:
            source = 'api'
            _clean_working_dir()
            local_file = download_from_api_server(api_file)
        else:
            _notify.send('File not found.')
            raise DmException('File not found.')
        return local_file, source

    if _notify is not None:
        set_notify(_notify)
    elif notify is None:
        raise InternalException('Notify is not setted.')
    remote_file = S3File(key)
    local_file, source = get_local_file()

    try:
        metadata = parse(local_file)
    except (InvalidDataFile, InvalidArchive):
        metadata = {'data_type': 'UNSUPPORTED'}
    else:
        if source == 's3':
            if not remote_file.is_compressed:
                remote_file.compress(local_file)
        elif source == 'api':
            if local_file.lower().endswith(settings.DMWORKER_COMPRESS_EXT):
                remote_file.compress(local_file)
            else:
                remote_file.upload(local_file)
    metadata['size'] = os.stat(local_file).st_size
    metadata['key'] = remote_file.key
    metadata['version'] = settings.DMWORKER_VERSION
    return metadata


def log_csv_stat(meta, errors):
    _f = lambda x: '' if x == 1 else 's'

    fatal_errors = [k['descr'] for k in errors if k['status'] == 'FATAL']
    # Few general error cases.
    if (meta['data_rows'] <= 1 and all([k == 'S' for k in meta['dtypes']])) or \
       (meta['data_rows'] <= 1 and all([k <= 1 for k in meta['uniques_per_col']])):
        fatal_errors.append(FORMAT_ERROR)
    if fatal_errors:
        notify.send(fatal_errors[0])
        raise InvalidCSV(fatal_errors[0])

    if meta['with_header']:
        notify.send("The dataset appears to have a header.")
    else:
        notify.send("No header found, first row contains data.")
    if meta['invalid_rows']:
        notify.send('Found %s row%s with invalid values:' % \
                    (meta['invalid_rows'], _f(meta['invalid_rows'])))
        for err in errors:
            if err['status'] == 'DATA':
                row = int(err['descr'][0]) + 1
                col = meta['names'][int(err['descr'][1])]
                notify.send('- row %s, column %s' % (row, col))
    notify.send('Found %s sample%s.' % \
                (meta['data_rows'], _f(meta['data_rows'])))
    for err in (e for e in errors if e['status'] not in ('DATA', 'INFO',)):
        notify.send(err['descr'])


def fill_distrib(metadata, source):

    def _loads(obj, kls):
        if isinstance(obj, kls):
            return obj
        if isinstance(obj, basestring):
            obj = obj.strip()
            try:
                if kls == list:
                    if obj[0] != '[' and obj[-1] != ']':
                        obj = '[%s]' % obj.replace('\n', ',').replace(',,', ',')
                elif kls == dict:
                    if obj[0] != '{' and obj[-1] != '}':
                        obj = '{%s}' % obj
            except IndexError:
                return kls() # empty instance
        return json.loads(obj)
    
    notify.send('Analyzing data...')
    meta, errors = ProcessCall('csvstat','parse', source).call()

    errors = _loads(errors, list)
    meta = _loads(meta, dict)
    if not meta or len(meta) == 0:
        notify.send(FORMAT_ERROR)
        raise InvalidCSV(FORMAT_ERROR)

    metadata.update(meta)
    log_csv_stat(metadata, errors)

    return metadata


def parse(fp):
    if fp.lower().endswith(settings.DMWORKER_SINGLE_FILE_EXT):
        metadata = parse_single_file(fp)
        if metadata['data_type'] in ['IMAGES', 'GENERAL']:
            metadata = fill_distrib(metadata, fp)
    else:
        try:
            with Archive(fp) as archive:
                metadata = parse_archive(archive)
        except InvalidArchive as e:
            msg = 'Unknown file format.'
            log.critical(msg)
            notify.send(msg)
            raise e
    return metadata


class LastColumnCounter(object):
    def __init__(self):
        self.data = None

    def _init_data(self, val):
        self.data = {
            'classes': Counter(),
            'max': val,
            'min': val,
            'set': set([val])
        }

    def update(self, val):
        if self.data is None:
            self._init_data(val)
        data = self.data
        if data['classes'] is not None:
            if int(val) == val:
                data['classes'].update({str(int(val)): 1})
            else:
                data['classes'] = None
        data['min'] = min(val, data['min'])
        data['max'] = max(val, data['max'])
        if data['set'] is not None:
            if len(data['set']) > 1000:
                data['set'] = None
            else:
                data['set'].add(val)
                if len(data['set']) > 200:
                    data['classes'] = None

    def get_result(self):
        if self.data is None:
            return {}
        data = self.data.copy()
        if data['set'] is None:
            data['unique'] = None
        else:
            data['unique'] = len(data['set'])
        del data['set']
        if data['classes'] is not None:
            data['classes'] = dict(data['classes'])
        return data


class ProcessNotify(object):
    def __init__(self, msg,
                 every_seconds=settings.DMWORKER_PROCCESS_NOTIFY_INTERVAL):
        self.msg = msg
        self.interval = dt.timedelta(seconds=every_seconds)
        self.time = dt.datetime.utcnow() + self.interval

    def __call__(self, fmt):
        if dt.datetime.utcnow() > self.time:
            notify.send(self.msg % fmt)
            self.time = dt.datetime.utcnow() + self.interval


def parse_csv(rows):
    num_columns = delimiter = None
    data_rows = empty_rows = invalid_rows = 0
    classes = LastColumnCounter()
    try:
        first_row = next(rows).strip().replace('\xef\xbb\xbf', '')
    except StopIteration:
        first_row = None
    if not first_row:
        msg = ("First row is empty, it must contain headers or data.")
        notify.send(msg)
        notify.send("This means your file isn't properly formatted")
        notify.send("(or you submitted another type of file).")

        raise InvalidCSV(msg)
    if ',' in first_row:
        delimiter = r'\s*,\s*'
        notify.send('Parsing CSV with comma as delimiter.')
    elif re.search(r'\s+', first_row):
        delimiter = r'\s+'
        notify.send('Parsing CSV with whitespace (tab) as delimiter.')
    else:
        msg = "CSV doesn't contain a valid delimiter."
        #TODO: use magic to detect type of file uploaded
        notify.send("CSV doesn't contain a valid delimiter.")
        notify.send("This means your file isn't properly formatted")
        notify.send("(or you submitted another type of file).")
        raise InvalidCSV(msg)

    num_columns = re.split(delimiter, first_row)

    if first_row.count(',') == 1:
        num_columns = [x for x in num_columns if x != '']
    num_columns = len(num_columns)

    if num_columns > 1:
        notify.send("Found %s fields in first row, assume all the "
                    "rows have this number of fields." % num_columns)
    else:
        msg = ("With selected delimiter found only %s columns "
               "in first row, must be at least 2." % num_columns)
        notify.send(msg)
        notify.send("This means your file isn't properly formatted")
        notify.send("(or you submitted another type of file).")
        raise InvalidCSV(msg)
    notify.send('Parsing...')
    meta = {
        'data_type': 'GENERAL',
        'num_columns': num_columns,
        'delimeter': delimiter
    }
    return meta


def parse_timestep(inv, outv, classes, binary_in, binary_out):
    try:
        inv = [float(v) for v in inv]
        outv = [float(v) for v in outv]
    except ValueError:
        msg = 'Non-float value in data file.'
        log.critical(msg)
        notify.admin_send(msg)
        notify.send(msg)
        raise InvalidTimeseries(msg)
    if binary_in and set(inv) != set([0.0, 1.0]):
        binary_in = False
    if binary_out:
        if set(outv) != set([0.0, 1.0]) or sum(outv) != 1:
            binary_out = False
            classes = Counter()
        else:
            classes.update({str(outv.index(1.0)): 1})
    return classes, binary_in, binary_out


def parse_ts(lines):
    data_rows = empty_rows = 0
    min_timesteps = max_timesteps = dim = None
    classes = Counter()
    binary_in = binary_out = True
    regexp = r'^(?:(?:{ft}\,)*{ft}\|(?:{ft}\,)*{ft}\;)+$'.format(ft=RE_FLOAT)
    regexp_in = r'^(?:(?:{ft}\,)*{ft}\;)+$'.format(ft=RE_FLOAT)
    regexp, regexp_in = re.compile(regexp), re.compile(regexp_in)
    regexps = [(regexp,
                lambda x: x.count('|'),
                lambda x: [y.split(',') for y in x.split('|')]),
               (regexp_in,
                lambda x: x.count(';'),
                lambda x: (x.split(','), []))
    ]

    process_notify = ProcessNotify(msg="%s lines parsed.")
    for i, line in enumerate(lines):
        i = i + 1
        line = line.strip().replace(' ', '').replace('\t', '')
        if line == '':
            empty_rows += 1
            continue
        if not line.endswith(';'):
            line += ';'
        if regexps[0][0].match(line):
            _, timesteps_fn, splitter_fn = regexps[0]
        elif regexps[1][0].match(line):
            _, timesteps_fn, splitter_fn = regexps[1]
            # if we hit second regexp on first line we assume what all
            # lines will hit this regexp, so we want to hit it as first
            # regexp, thats why we reverse regexps
            regexps.reverse()
        else:
            msg = ('Not allowed character or improperly formatted timeseries '
                   'on line %s.' % i)
            log.critical(msg)
            notify.send(msg)
            raise InvalidTimeseries(msg)

        timesteps = timesteps_fn(line)
        if min_timesteps is None or min_timesteps > timesteps:
            min_timesteps = timesteps
        if max_timesteps is None or max_timesteps < timesteps:
            max_timesteps = timesteps
        for j, timestep in enumerate(line.strip(';').split(';')):
            j = j + 1
            inv, outv = splitter_fn(timestep)
            if dim is None:
                dim = (len(inv), len(outv))
                notify.send('First timestep has %s inputs and %s outputs. '
                            'Applying this requirement to the '
                            'entire file.' % dim)
            elif (len(inv), len(outv)) != dim:
                msg = ('Oops! Timestep %s on line %s has %s '
                       'inputs and %s outputs.' % (j, i, len(inv), len(outv)))
                log.critical(msg)
                notify.send(msg)
                raise InvalidTimeseries(msg)
            classes, binary_in, binary_out = parse_timestep(
                inv, outv, classes, binary_in, binary_out
            )
        data_rows += 1
        process_notify((i,))

    if data_rows == 0:
        msg = 'File contains no data.'
        log.critical(msg)
        notify.send(msg)
        raise InvalidTimeseries(msg)
    else:
        meta = {
            'data_type': 'TIMESERIES',
            'data_rows': data_rows,
            'empty_rows': empty_rows,
            'min_timesteps': min_timesteps,
            'max_timesteps': max_timesteps,
            'input_size': dim[0],
            'output_size': dim[1],
            'classes': dict(classes),
            'binary_input': binary_in,
            'binary_output': binary_out,
        }
        return meta


def parse_single_file(filename):
    is_ext = lambda x: filename.lower().endswith(x)
    if is_ext('.csv'):
        return parse_csv(open_file(filename))
    elif is_ext('.ts'):
        return parse_ts(open_file(filename))
    elif is_ext('.csv.gz'):
        return parse_csv(open_gz(filename))
    elif is_ext('.ts.gz'):
        return parse_ts(open_gz(filename))
    elif is_ext(('.csv.bz', '.csv.bz2')):
        return parse_csv(open_bz(filename))
    elif is_ext(('.ts.bz', '.ts.bz2')):
        return parse_ts(open_bz(filename))
    msg = 'Unknown file format.'
    log.critical(msg)
    notify.admin_send(msg)
    notify.send(msg)
    raise InvalidDataFile(msg)


def parse_archive(archive):
    classes = Counter()
    img_cnt = 0
    skipped = 0
    imgs_found = False

    for member in archive:
        if member.lower().endswith(settings.DMWORKER_IMAGES_EXT):
            if not imgs_found:
                notify.send('Image dataset unpacked. Parsing...')
                imgs_found = True
            process_notify = ProcessNotify(msg="%s images parsed.")
            klass = archive.get_img_class(member)
            img_cnt += 1
            if klass is None:
                skipped += 1
            else:
                classes.update({klass: 1})
            process_notify((img_cnt,))
        elif member.lower().endswith(settings.DMWORKER_TIMESERIES_EXT):
            notify.send('Timeseries data %s unpacked. Parsing...' % member)
            ts = archive.open_member(member)
            meta = parse_ts(ts)
            meta['archive_path'] = member
            return meta
        elif member.lower().endswith(settings.DMWORKER_GENERAL_EXT):
            notify.send('CSV file %s unpacked.' % member)
            csv = archive.open_member(member)
            meta = parse_csv(csv)
            with TempFile() as tf:
                with open(tf, 'w') as f:
                    for line in archive.open_member(member):
                        line += '\n'
                        f.write(line.replace('\n\n', '\n'))
                meta = fill_distrib(meta, tf)            
            meta['archive_path'] = member
            return meta
    if classes:
        notify.send('%s images found.' % img_cnt)
        if skipped:
            notify.send(('Skipped %s images with leading dot '
                         'or without class.') % skipped)
        meta = {
            'classes': dict(classes),
            'data_type': 'IMAGES',
        }
        return meta
    else:
        msg = 'This file doesn\'t contain a supported data format.'
        log.critical(msg)
        notify.send(msg)
        raise InvalidDataFile(msg)
