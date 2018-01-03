import unittest
import cStringIO
from ersatz.data.formats import CsvDataFile
from ersatz.exception import DataFileError


def io(data):
    return cStringIO.StringIO(data)


class TestCsv(unittest.TestCase):

    def test_parser_invalid(self):
        invalid = io('')
        with self.assertRaises(DataFileError):
            CsvDataFile(invalid)
        invalid = io('1,2 3')
        with self.assertRaises(DataFileError):
            CsvDataFile(invalid)
            invalid = io('abc')
        with self.assertRaises(DataFileError):
            CsvDataFile(invalid)

    def test_parser(self):
        valid = io('.0e+00,0.0e+000,1.2,2,  .33, 100., 1.2')
        df = CsvDataFile(valid)
        self.assertEqual(df.delimiter, ',')

    def test_parser_comma(self):
        valid = io('.0e+00,0.0e+000,1.2,2,  .33, 100, ')
        df = CsvDataFile(valid)
        self.assertEqual(df.delimiter, ',')
        valid = io('.0e+00,0.0e+000,1.2,2,  .33\n2 2 3 4 5')
        df = CsvDataFile(valid)
        self.assertEqual(df.delimiter, ',')
        valid = io('.0e+00,0.0e+000,1.2,2,  .33\r\n2 2 3 4 5')
        df = CsvDataFile(valid)
        self.assertEqual(df.delimiter, ',')
        invalid = io('.0e+00,0.0e+000,1.2,2,  .33\\n2, 3, 4')
        with self.assertRaises(DataFileError):
            df = CsvDataFile(invalid)

    def test_parser_space(self):
        valid = io('.0e+00 0.0e+000 1.2 2   .33')
        df = CsvDataFile(valid)
        self.assertEqual(df.delimiter, None)
        valid = io('.0e+00 0.0e+000 1.2 2   .33\n2, 2, 3, 4, 5')
        df = CsvDataFile(valid)
        self.assertEqual(df.delimiter, None)
        valid = io('.0e+00 0.0e+000 1.2 2   .33\r\n2, 2, 3, 4, 5')
        df = CsvDataFile(valid)
        self.assertEqual(df.delimiter, None)
        invalid = io('.0e+00 0.0e+000 1.2 2   .33\\n2  3  4')
        with self.assertRaises(DataFileError):
            df = CsvDataFile(invalid)

    def test_parser_header(self):
        header = "First, Second, Third, etc"
        valid = io(header + '1 2  3 4\n3 4 5 6')
        df = CsvDataFile(valid)
        self.assertEqual(df.delimiter, None)

    def test_parser_backtrack(self):
        print 'This will run forever in case of catastrophic backtrack.'
        valid = "0.0 0.0 0.0 0.0 0.0 0.328125 0.72265625 0.62109375 0.58984375"
        valid = " ".join(valid for _ in range(50))
        spaces = valid
        validio = io(valid)
        df = CsvDataFile(validio)
        self.assertEqual(df.delimiter, None)
        validio = io(valid.replace(' ', ', '))
        df = CsvDataFile(validio)
        self.assertEqual(df.delimiter, ',')

        valid = valid + '\n' + valid
        validio = io(valid)
        df = CsvDataFile(validio)
        self.assertEqual(df.delimiter, None)
        valid = valid.replace(' ', ', ')
        validio = io(valid)
        df = CsvDataFile(validio)
        self.assertEqual(df.delimiter, ',')

        invalid = spaces + '\\n' + spaces
        invalidio = io(invalid)
        with self.assertRaises(DataFileError):
            df = CsvDataFile(invalidio)
        invalid = invalid.replace(' ', ', ')
        invalidio = io(invalid)
        with self.assertRaises(DataFileError):
            df = CsvDataFile(invalidio)
        print 'Catastrophic backtrack not found!'
