Indexed Lines Random Access File Reader
=======================================================================================================================

Provides an simple line start offsets index to quickly read text file
random line or line ranges specified by line numbers.

Requires writable path to store index file.

Example usage:

.. code-block::
    :language: python

    from indexed_lines_reader.base import IndexedLinesReader
    reader = IndexedLinesReader()
    reader.index_path = './'
    reader.data_path = './huge_text_file.txt'
    reader.make_index_file()

    line_54321 = reader.get_line_by_index(54321)

    for line in reader.lines(123456, 234567):  # this is a lines generator
         do_something_useful(line)


Internally it uses mmap to keep source file and index in memory when possible.

.. seealso::
    `https://pypi.org/project/mtFileUtil/`_
    `random-access-file-reader <https://pypi.org/project/random-access-file-reader/>`_
