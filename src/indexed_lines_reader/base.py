import hashlib
import mmap
import os
from os import path


class IndexedLinesReader(object):
    __slots__ = ['_file_path', '_index_path', '_lines_index', '_index_loaded', '_index_fh', '_data_fh', '_lines_count']
    index_values_byteorder = 'big'
    index_value_size = 4

    class PathIsNotSet(Exception):

        def __init__(self, expected_attribute):
            self._attr = expected_attribute

        def __str__(self):
            return f"Path is not set: {self._attr}"

    class IndexError(Exception):

        def __init__(self, msg):
            self._msg = msg

        def __str__(self):
            return self._msg

    def __init__(self):
        super().__init__()
        self._file_path = None
        self._index_path = None
        self._lines_index = []
        self._index_loaded = False
        self._index_fh = None
        self._data_fh = None
        self._lines_count = None

    @property
    def index_path(self):
        """Get index file directory path"""
        return self._index_path

    @index_path.setter
    def index_path(self, index_path):
        """Set index file directory path"""
        assert isinstance(index_path, str)
        assert path.exists(index_path), f"Index path must exists: {index_path}"
        assert path.isdir(index_path), f"Index path must be dir: {index_path}"
        self._index_path = index_path

    @property
    def data_path(self):
        """Get data file path"""
        return self._file_path

    @data_path.setter
    def data_path(self, file_path):
        """Set data file path"""
        assert isinstance(file_path, str), f"File path must be string, not {type(file_path).__name__}"
        assert path.exists(file_path), f"File path {file_path} is not exists"
        assert path.isfile(file_path), f"Path {file_path} must be file path"
        self._file_path = file_path

    @property
    def lines_count(self):
        """Get data file lines count. Returns None if index is not opened"""
        return self._lines_count or None

    @property
    def index_loaded(self):
        """Check if index loaded"""
        return self._index_loaded

    def get_index_file_path(self):
        """Generate index file path for source file"""
        if self._file_path is None:
            raise self.PathIsNotSet('data_path')
        return path.join(self.index_path, hashlib.md5(self.data_path.encode()).hexdigest() + '.idx')

    def i2b(self, int_value):
        """Translate integer to storable bytes format"""
        return int_value.to_bytes(self.index_value_size, signed=False, byteorder=self.index_values_byteorder)

    def b2i(self, bytes_value):
        """Translate storable bytes format to integer"""
        assert isinstance(bytes_value, bytes)
        assert len(bytes_value) == self.index_value_size
        return int.from_bytes(bytes_value, signed=False, byteorder=self.index_values_byteorder)

    def make_index_file(self, raise_if_exists=False, keep_file_opened=False):
        """Calculate data file lines index"""
        if self._file_path is None:
            raise self.PathIsNotSet('data_path')
        if self._index_path is None:
            raise self.PathIsNotSet('index_path')
        index_file_path = self.get_index_file_path()
        index_file_base_name = path.basename(index_file_path)
        if path.exists(index_file_path):
            if raise_if_exists:
                raise RuntimeError(f"Index file {index_file_base_name} already exists")
            os.remove(index_file_path)

        self.ensure_data_file_opened()
        self._data_fh.seek(0)

        self._index_fh = open(index_file_path, 'wb')
        current_pos = 0
        while True:
            self._index_fh.write(self.i2b(current_pos))
            line = self._data_fh.readline()
            if current_pos == self._data_fh.tell():
                break
            current_pos = self._data_fh.tell()

        if not keep_file_opened:
            self.close_data_file()

        self.close_index_file()

    def open_index_file(self, create_if_not_exists=False):
        """Open index file"""
        index_file_path = self.get_index_file_path()
        if not path.exists(index_file_path):
            if create_if_not_exists:
                self.make_index_file()
        fh = open(index_file_path, 'rb')
        self._index_fh = mmap.mmap(fh.fileno(), 0, access=mmap.ACCESS_READ)

        file_size = path.getsize(index_file_path)
        self._lines_count = file_size // self.index_value_size

    def ensure_index_file_opened(self):
        """Open index file if not opened before"""
        if self._index_fh is None:
            self.open_index_file()

    def close_index_file(self):
        """Close index file if not close yet"""
        if self._index_fh is None:
            return
        self._index_fh.close()
        self._index_fh = None

    def get_line_offset(self, line_number):
        """Get line offset in data file by line number"""
        self.ensure_index_file_opened()
        index_offset = line_number * self.index_value_size
        self._index_fh.seek(index_offset)
        if not self._index_fh.tell() == index_offset:
            raise self.IndexError(
                f"Failed seek to index offset {index_offset:#x}/{index_offset}: file tells pos {self._index_fh.tell()}"
            )
        bytes_value = self._index_fh.read(self.index_value_size)
        if bytes_value == b'':
            raise self.IndexError(
                f"Failed detect line offset by number {line_number}: "
                f"index_offset {index_offset:#x}/{index_offset} {self.index_value_size}-bytes value empty"
            )
        return self.b2i(bytes_value)

    def get_line_by_index(self, line_number):
        self.ensure_index_file_opened()
        start_index = self.get_line_offset(line_number)
        self.ensure_data_file_opened()
        self._data_fh.seek(start_index)
        return self._data_fh.readline()

    def lines(self, start_idx, end_idx=None):
        """Get data file line from start to end indexes"""
        assert isinstance(start_idx, int)
        if start_idx == end_idx or end_idx is None:
            yield self.get_line_by_index(start_idx)
            return
        assert isinstance(end_idx, int)
        if end_idx < start_idx:
            raise IndexError(f"Ending index must be greater then starting: lines({start_idx}, {end_idx})")

        if self._file_path is None:
            raise self.PathIsNotSet('data_path')
        if self._index_path is None:
            raise self.PathIsNotSet('index_path')
        self.ensure_index_file_opened()
        self.ensure_data_file_opened()

        lines_count = end_idx - start_idx
        start_index = self.get_line_offset(start_idx)
        self._data_fh.seek(start_index)
        idx = 0
        while idx <= lines_count:
            yield self._data_fh.readline().strip()
            idx += 1

    def lines_from(self, start_idx, lines_count):
        """Get data file lines count from start indexes not more then requested count"""
        for x in self.lines(start_idx, start_idx + lines_count-1):
            yield x

    def open_data_file(self):
        """Open data file"""
        if self._file_path is None:
            raise self.PathIsNotSet('data_path')
        fh = open(self._file_path, mode='r', buffering=8196)
        self._data_fh = mmap.mmap(fh.fileno(), 0, access=mmap.ACCESS_READ)

    def close_data_file(self):
        """Close data file"""
        if self._data_fh is None:
            pass
        self._data_fh.close()
        self._data_fh = None

    def ensure_data_file_opened(self):
        """Open data file if not opened before"""
        if self._data_fh is None:
            self.open_data_file()
