import random
import string
from datetime import datetime
from pathlib import Path

import pytest

from indexed_lines_reader.base import IndexedLinesReader


@pytest.fixture
def class_to_test():
    return IndexedLinesReader


@pytest.fixture
def instance_to_test(class_to_test):
    return class_to_test()


@pytest.fixture
def generate_text_lines():
    def _(max_lines):
        line_idx = 0
        for _ in range(0, max_lines):
            line = ""
            line += f'{line_idx:0=8d} '
            line += ''.join(random.choice(string.ascii_letters) for x in range(5, random.randint(10, 50)))
            if _ < max_lines:
                line += "\n"
            yield line
            line_idx += 1

    return _


@pytest.fixture
def couple_tens_of_ascii_lines(generate_text_lines):
    random_text = []
    line_idx = 0
    for line in generate_text_lines(10 * random.randint(2, 5)):
        random_text.append(line)
        line_idx += 1
    # return with last \n strip
    return ''.join(random_text)


@pytest.fixture
def tmp_file_path(tmp_path):
    return tmp_path / ''.join(random.choice(string.ascii_letters) for _ in range(random.randint(5, 15)))


@pytest.fixture
def indexer_for_lines_count(class_to_test, tmp_file_path, tmpdir, generate_text_lines):
    def _(data_file_size):
        instance = class_to_test()
        if tmp_file_path.exists():
            tmp_file_path.unlink()
        with tmp_file_path.open('wb') as test_fh:
            test_fh.writelines((x.encode() for x in generate_text_lines(data_file_size)))
        instance.index_path = str(tmpdir)
        instance.data_path = str(tmp_file_path)

        index_file_path = Path(instance.get_index_file_path())
        if index_file_path.exists():
            index_file_path.unlink()
        return instance

    return _


@pytest.fixture
def random_text_file(couple_tens_of_ascii_lines, tmp_file_path):
    with tmp_file_path.open('wb') as test_fh:
        test_fh.write(''.join(x for x in couple_tens_of_ascii_lines if x).encode())
    return tmp_file_path


def test_init(instance_to_test, class_to_test):
    instance = instance_to_test
    assert isinstance(instance, class_to_test)


def test_base_instance_init_nothing(instance_to_test):
    assert instance_to_test.data_path is None
    assert instance_to_test.index_path is None


def test_base_instance_methods_raises(instance_to_test, class_to_test):
    with pytest.raises(class_to_test.PathIsNotSet):
        instance_to_test.make_index_file()
    with pytest.raises(class_to_test.PathIsNotSet):
        instance_to_test.open_data_file()
    with pytest.raises(class_to_test.PathIsNotSet):
        instance_to_test.open_index_file()
    with pytest.raises(class_to_test.PathIsNotSet):
        instance_to_test.get_line_offset(0)
    with pytest.raises(class_to_test.PathIsNotSet):
        for line in instance_to_test.lines(0, 1):
            pass


def test_create_index(instance_to_test, tmpdir, random_text_file):
    instance_to_test.index_path = str(tmpdir)
    instance_to_test.data_path = str(random_text_file)
    expected_name = instance_to_test.get_index_file_path()
    instance_to_test.make_index_file()
    assert (Path(instance_to_test.index_path) / expected_name).exists()


def test_index_len(instance_to_test, tmpdir, random_text_file):
    instance_to_test.index_path = str(tmpdir)
    instance_to_test.data_path = str(random_text_file)
    file_data = random_text_file.read_text()
    file_lines = file_data.split("\n")

    instance_to_test.make_index_file()
    instance_to_test.ensure_index_file_opened()
    if not instance_to_test.lines_count == len(file_lines):
        raise AssertionError(
            f"Incorrect lines count detection in {file_lines}: "
            f"data len {len(file_lines)} lines reported as {instance_to_test.lines_count} by indexer"
        )


def test_line_offsets(instance_to_test, tmpdir, random_text_file):
    instance_to_test.index_path = str(tmpdir)
    instance_to_test.data_path = str(random_text_file)
    file_data = random_text_file.read_text()
    file_lines = file_data.split("\n")

    instance_to_test.make_index_file()
    instance_to_test.ensure_index_file_opened()
    for idx, written in enumerate(file_lines):
        if not written:
            continue
        line_pos = file_data.index(written)
        assert line_pos == instance_to_test.get_line_offset(idx)


def test_single_line_read_by_idx(instance_to_test, tmpdir, random_text_file):
    instance_to_test.index_path = str(tmpdir)
    instance_to_test.data_path = str(random_text_file)
    file_data = random_text_file.read_text()
    file_lines = file_data.split("\n")

    instance_to_test.make_index_file()
    instance_to_test.ensure_index_file_opened()
    for idx, written in enumerate(file_lines):
        if not written:
            continue
        line_pos = file_data.index(written)
        if not line_pos == instance_to_test.get_line_offset(idx):
            raise AssertionError(
                f"Line {written} is not found in test data"
            )

        taken_line = (instance_to_test.get_line_by_index(idx)).decode().strip()
        assert taken_line == written


def test_get_lines_by_index(instance_to_test, tmpdir, random_text_file):
    instance_to_test.index_path = str(tmpdir)
    instance_to_test.data_path = str(random_text_file)
    file_data = random_text_file.read_text()
    file_lines = file_data.split("\n")

    instance_to_test.make_index_file()
    instance_to_test.ensure_index_file_opened()
    for idx, written in enumerate(file_lines):

        taken = [x for x in instance_to_test.lines(idx, idx + 1)]
        assert len(taken) == 2


def test_different_file_access_time(indexer_for_lines_count):
    target_index_rpm = 10000
    target_slice_rpm = 200000

    for data_file_size in [1000, 2000, 5000, 10000]:
        instance = indexer_for_lines_count(data_file_size)
        started = datetime.now()
        instance.make_index_file(raise_if_exists=True)
        make_index_time = (datetime.now() - started).total_seconds()
        rpm = data_file_size / make_index_time
        if rpm < target_index_rpm:
            raise AssertionError(
                f"Indexing rpm below {rpm} < {target_index_rpm} "
                f"on {data_file_size} lines file {instance.data_path}"
            )
        instance.ensure_index_file_opened()
        instance.ensure_data_file_opened()
        for x in range(0, instance.lines_count - 1):
            try:
                start_idx = instance.get_line_offset(x)
            except Exception as exc:
                raise AssertionError(
                    f"Error find line {x} offset "
                    f"on {data_file_size} lines file {instance.data_path}: {exc}"
                )

        for _ in range(100):
            random_size = random.randint(20, 120)
            random_start = random.randint(0, data_file_size - random_size - 1)
            random_end = random_start + random_size
            started = datetime.now()
            try:
                lines = [x for x in instance.lines(random_start, random_end)]
            except Exception as exc:
                try:
                    start_idx = instance.get_line_offset(random_start)
                except Exception as exc:
                    raise AssertionError(
                        f"Error slicing [{random_start}:{random_end}] "
                        f"on {data_file_size} lines file {instance.data_path}: "
                        f"line {random_start} offset index detect error: {exc}"
                    )
                raise AssertionError(
                    f"Error slicing [{random_start}:{random_end}] "
                    f"on {data_file_size} lines file {instance.data_path}, start offset {start_idx}"
                )
            time_taken = (datetime.now() - started).total_seconds()
            rpm = len(lines) / time_taken
            if rpm < target_slice_rpm:
                raise AssertionError(
                    f"Rpm below {rpm}<{target_slice_rpm} "
                    f"slicing [{random_start}:{random_end}] "
                    f"on {data_file_size} lines file {instance.data_path}"
                )
