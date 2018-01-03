#ifndef ERSATZ_UTILS_io_h
#define ERSATZ_UTILS_io_h

#include <string>
#include <iostream>
#include <fstream>

#include <boost/spirit/include/qi.hpp>
#include <boost/filesystem.hpp>
#include <boost/iostreams/filtering_streambuf.hpp>
#include <boost/iostreams/filtering_stream.hpp>
#include <boost/iostreams/copy.hpp>
#include <boost/iostreams/filter/gzip.hpp>
#include <boost/iostreams/filter/bzip2.hpp>

#include <ersatz/utils/String.h>

namespace ersatz
{
namespace utils
{

std::ifstream::pos_type getFileSize(const std::string& file_name)
{
  std::ifstream in(file_name, std::ifstream::ate | std::ifstream::binary);
  E_USER_ASSERT(in, "Cannot open file: " + file_name);
  return in.tellg();
}

class FileReader
{
public:
  FileReader(const std::string& file_name)
  {
    std::string ext = boost::filesystem::extension(file_name);

    file.reset(new std::ifstream(file_name));
    E_USER_ASSERT(!(file->fail()), "Cannot open file: " + file_name);

    filter.reset(new boost::iostreams::filtering_istream());

    if (ext == ".gz")
      filter->push(boost::iostreams::gzip_decompressor());
    else if (ext == ".bz" || ext == ".bz2")
      filter->push(boost::iostreams::bzip2_decompressor());

    filter->push(*file);
  }

  std::istream& getInput()
  {
    return *filter;
  }
private:
  std::shared_ptr<std::ifstream> file;
  std::shared_ptr<boost::iostreams::filtering_istream> filter;
};

bool readLine(std::istream& in, StrRef& line)
{
  static std::string str;
  if (!std::getline(in, str))
    return false;

  // for windows compatiblity (\r\n line end)
  if (!str.empty() && str.back() == '\r')
    str.resize(str.size() - 1);

  line.assign(str.c_str(), str.size());
  return true;
}

/**
 * Read line that handles mac (\r), linux (\n) and windows (\r\n) line end.
 *
 * TODO: this can be done more efficinety with SSE4.2 string instructions
 */
bool readLineAllOS(std::istream& is, std::string& str)
{
  str.clear();
  std::streambuf* sb = is.rdbuf();
  for (;;)
  {
    int c = sb->sbumpc();
    switch (c)
    {
    case '\n':
      return true;
    case '\r':
      if (sb->sgetc() == '\n')
        sb->sbumpc();
      return true;
    case EOF:
      return !str.empty();
    default:
      str += (char) c;
    }
  }
}

bool readLineAllOS(std::istream& in, StrRef& line)
{
  static std::string str;

  if (!readLineAllOS(in, str))
    return false;

  line.assign(str.c_str(), str.size());
  return true;
}

class CSVParser
{
public:
  typedef std::vector<StrRef> Record;
public:
  CSVParser() :
      first(true)
  {
  }

  bool readNextRecord(std::istream& in)
  {
    if (!readLineAllOS(in, line))
      return false;

    if (first)
    {
      guessSeparator();
      parseRecord();
      guessHeader();
      first = false;
    }
    else
    {
      is_header = false;
      parseRecord();
    }
    return true;
  }

  char getSeparator() const
  {
    return sep;
  }

  std::string getPrettySeparator() const
  {
    if (sep == ',')
      return "\\s*,\\s*";
    else if (sep == '\t')
      return "\\s+";
    else
      return "\\s+";
  }

  const Record& getRecord() const
  {
    return record;
  }

  const StrRef& getLine() const
  {
    return line;
  }

  bool isHeader() const
  {
    return is_header;
  }
private:
  /**
   * Guess the separator.
   * Heuristc: first occurence of a valid separator (' ',',','\t' ) will be the separator.
   */
  void guessSeparator()
  {
    bool in_quotes = false;
    for (const char * p = line.str(); p != line.end(); ++p)
    {
      if( *p=='"' )
        in_quotes = !in_quotes;

      if(in_quotes)
        continue;

      if (*p == '\t' || *p == ',' || *p == ' ')
      {
        sep = *p;
        return;
      }
    }
    E_USER_FAIL("CSV doesn't contain a valid delimiter.\nThis means your file isn't properly formatted\n(or you submitted another type of file).");
  }

  /*
   * Guess if it is a header.
   * Heuristic: if all fields are string we consider it as a header.
   */
  void guessHeader()
  {
    float x;
    is_header = true;
    for (auto it = record.begin(); it != record.end(); ++it)
    {
      const char * p = it->str();
      if (boost::spirit::qi::parse(p, it->end(), x))
      {
        is_header = false;
        return;
      }
    }
  }

  inline void parseRecord()
  {
    if( sep == ' ' )
      parseRecordWithOptionallyQuotedFields<true>(); // for spaces we treat separator sequences as one separator
    else
      parseRecordWithOptionallyQuotedFields<false>();
  }

  void fastParseRecord()
  {
    record.clear();
    const char * p = line.str();
    while (p != line.end())
    {
      const char * q = (const char *) memchr(p, sep, line.end() - p);
      if (q)
      {
        record.push_back(StrRef(p, q));
        p = q + 1;
      }
      else
      {
        record.push_back(StrRef(p, line.end()));
        return;
      }
    }
    if (!line.isEmpty() && *(line.end() - 1) == sep)
      record.push_back(StrRef());
  }

  inline void trimAndAddField( const char * p, const char * q )
  {
    // cut leading and trailing space
    while( *p == ' ' && p<q )
      p++;
    q--;
    while( q>p && *q == ' ' )
      q--;
    record.push_back(StrRef(p, q+1));
  }

  template<bool SKIP_SEP_SEQ = false>
  void parseRecordWithOptionallyQuotedFields()
  {
    record.clear();
    const char * p = line.str();
    while (p != line.end())
    {
      if( *p == '"' )
      {
        // quoted field
        ++p;
        const char * q = (const char *) memchr(p, '"', line.end() - p); // find ending quote
        if( q )
        {
          record.push_back(StrRef(p, q));
          p = q + 1;
          const char * q = (const char *) memchr(p, sep, line.end() - p);
          if(!q)
            return;
          p = q + 1;
          if( SKIP_SEP_SEQ )
            while( p != line.end() && *p == sep )
              ++p;
        }
        else
        {
          // no ending quote
          record.push_back(StrRef(p, line.end()));
          return;
        }
      }
      else
      {
        // unquoted field
        const char * q = (const char *) memchr(p, sep, line.end() - p);
        if (q)
        {
          trimAndAddField(p,q);
          p = q + 1;
          if( SKIP_SEP_SEQ )
            while( p != line.end() && *p == sep )
              ++p;
        }
        else
        {
          trimAndAddField(p,line.end());
          return;
        }
      }
    }
    if (!line.isEmpty() && *(line.end() - 1) == sep)
      record.push_back(StrRef());
  }


protected:
  bool first;
  bool is_header;
  char sep;
  StrRef line;
  Record record;
};

} // namespace utils
} // namespace ersatz

#endif // ERSATZ_UTILS_io_h
