#ifndef ERSATZ_DM_CSVStat_h
#define ERSATZ_DM_CSVStat_h

#include <map>
#include <set>
#include <vector>
#include <limits>
#include <fstream>
#include <unordered_map>
#include <boost/lexical_cast.hpp>
#include <Jzon.h>
#include <ersatz/utils/Error.h>
#include <ersatz/utils/String.h>
#include <ersatz/utils/io.h>
#include <ersatz/utils/SimpleStat.h>
#include <ersatz/utils/Histogram.h>
#include <ersatz/utils/Unique.h>
#include <ersatz/dm/Common.h>

namespace ersatz
{
namespace dm
{

typedef std::shared_ptr<ersatz::utils::Histogram<Float> > SPHist;

bool isInteger( double x )
{
  double int_part;
  double frac = modf(x,&int_part);
  return frac == 0;
}

bool isInteger( const ersatz::utils::StrRef& s )
{
  double x;
  if( !ersatz::utils::parseReal(x, s) )
    return false;
  return isInteger(x);
}

std::string formatAsInteger( const std::string& s )
{
  double x = 0;

  E_ASSERT( ersatz::utils::parseReal(x, s.c_str()) );

  double int_part;
  double frac = modf(x,&int_part);
  E_ASSERT( frac == 0 );

  return boost::lexical_cast<std::string>(int_part);
}

struct ColStat
{
  ColStat()
  {
    num_num = 0;
    string_num = 0;
    simple_stat.reset();
    strings.clear();
  }

  void update1(const ersatz::utils::StrRef& s)
  {
    if (s.isEmpty())
      return;

    // manage type
    if (string_num < 100)  // TODO: refine this
    {
      Float x;
      if (ersatz::utils::parseReal(x, s))
      {
        num_num++;
        simple_stat.add(x);
      }
      else
      {
        string_num++;
        strings.insert(std::string(s.str(), s.end()));
      }
    }

    // update unique values
    unique_values.add(s);
  }

  void pass1Finished()
  {
    using namespace ersatz::utils;

    // create histogram for numberic
    if (isNumeric())
    {
      // remove errors first
      for (auto it = strings.begin(); it != strings.end(); ++it)
        unique_values.removeAll(StrRef(it->c_str(), it->c_str() + it->size()));
      hist.reset(new Histogram<Float>(simple_stat.min(), simple_stat.max(), heuristicBinCount(unique_values.size())));
    }
  }

  /**
   * Second pass update (update histogram). Returns if the record is valid.
   */
  bool update2(const ersatz::utils::StrRef& s)
  {
    if (!s.isEmpty() && hist)
    {
      Float x;
      if (ersatz::utils::parseReal(x, s))
        hist->add(x);
      else
        return false;
    }
    return true;
  }

  void invalidate(const ersatz::utils::StrRef& s)
  {
    unique_values.remove(s);
    //if( hist )
    //hist.add(s,-1);
  }

  void pass2Finished()
  {
    using namespace ersatz::utils;

    if (hist || unique_values.size() == 0)
      return;

    // create the missing histogram
    hist.reset(new Histogram<Float>(0, unique_values.size() - 1, heuristicBinCount(unique_values.size())));
    StrUnique::SortedCountMap sorted = unique_values.getSortedCountMap();
    size_t i = 0;
    for (auto it = sorted.begin(); it != sorted.end(); ++it, ++i)
      hist->add(i, it->second);
  }

  bool isCategorical() const
  {
    return unique_values.size() <= 200;
  }

  bool isNumeric() const
  {
    return (num_num / (double) (string_num + num_num)) > 0.9;
  }

  bool isInt() const
  {
    if (!isNumeric() || !isCategorical() || simple_stat.min() < 0 || simple_stat.max() > 200 )
      return false;

    // check if they all parses as int
    for (auto it = unique_values.getCountMap().begin(); it != unique_values.getCountMap().end(); ++it)
      if( !isInteger(it->first) )
        return false;

    return true;
  }

  std::string getType() const
  {
    if (isNumeric())
    {
      if (isInt())
        return "i";
      else
        return "f";
    }
    else
    {
      if (isCategorical())
        return "S";
      else
        return "-";
    }
  }

  bool isLocked() const
  {
    return getType() != "i";
  }

  bool hasClasses() const
  {
    return getType() == "S";
  }

  bool lastColHasClasses() const
  {
    return getType()=="i" || getType() == "S";
  }

  std::set<std::string> strings;
  size_t string_num;
  size_t num_num;
  std::string name;
  ersatz::utils::StrUnique unique_values;
  SPHist hist;
  ersatz::utils::SimpleStat<Float> simple_stat;
};

typedef std::vector<ColStat> ColStats;

class CSVStat
{
public:
  void analize(const char * file_name, bool do_pass2 = true )
  {
    using namespace ersatz::utils;

    log_messages = 0;

    file_size = getFileSize(file_name);

    FileReader f1(file_name);

    report("Analyzing data phase 1...");
    pass1(f1.getInput());
    for (auto it = col_stats.begin(); it != col_stats.end(); ++it)
      it->pass1Finished();

    if( !do_pass2 )
      return;

    FileReader f2(file_name);
    report("Analyzing data phase 2...");
    pass2(f2.getInput());
    for (auto it = col_stats.begin(); it != col_stats.end(); ++it)
      it->pass2Finished();
  }

  const ColStats& getColStats() const
  {
    return col_stats;
  }

  bool hasHeader() const
  {
    return has_header;
  }

  void toJSON() const
  {
    using namespace Jzon;

    Object r;
    buildJSONOutput(r);
    Writer writer(r, StandardFormat);
    writer.Write();
    std::cout << writer.GetResult() << std::endl;
  }

private:
  /**
   * Pass1: detect type, collect uniques values, calc min, max
   */
  void pass1(std::istream& in)
  {
    using namespace ersatz::utils;

    col_stats.clear();

    CSVParser r;
    E_USER_ASSERT(r.readNextRecord(in), "First row is empty, it must contain headers or data.\nThis means your file isn't properly formatted\n(or you submitted another type of file).");

    // process first line
    delimiter = r.getPrettySeparator();
    col_stats.resize(r.getRecord().size());
    if (r.isHeader())
    {
      fillColNamesFromHeader(r.getRecord());
      has_header = true;
    }
    else
    {
      fillColNamesWithNumbers();
      has_header = false;
      pass1processRecord(r.getRecord());
    }

    // process lines
    while (r.readNextRecord(in))
      pass1processRecord(r.getRecord());
  }

  void pass1processRecord(const ersatz::utils::CSVParser::Record& r)
  {
    if (r.size() >= col_stats.size())  // not empty or truncated
    {
      for (size_t i = 0; i < r.size(); ++i)
        col_stats[i].update1(r[i]);
    }
  }

  /**
   * Pass2: build histograms, collect errors
   */
  void pass2(std::istream& in)
  {
    using namespace ersatz::utils;

    valid_data_rows = 0;
    empty_rows = 0;
    invalid_rows = 0;

    CSVParser r;
    size_t row = 0;
    if (has_header)
    {
      r.readNextRecord(in);
      row++;
    }
    for (; r.readNextRecord(in); ++row)
    {
      const CSVParser::Record &rec = r.getRecord();

      // empty row
      if (rec.size() == 0)
      {
        empty_rows++;
        continue;
      }

      // truncated row
      if (rec.size() < col_stats.size())
      {
        invalid_rows++;
        reportDataError(row, rec.size());
        continue;
      }

      // valid row?
      bool valid = true;
      valid_data_rows++;
      for (size_t col = 0; col < rec.size(); ++col)
      {
        if (!col_stats[col].update2(rec[col]))
        {
          reportDataError(row, col);
          valid = false;
          break;
        }
      }

      if (!valid)
      {
        valid_data_rows--;
        invalid_rows++;
        for (size_t col = 0; col < rec.size(); ++col)
          col_stats[col].invalidate(rec[col]);
      }
    }
  }

  void fillColNamesFromHeader(const ersatz::utils::CSVParser::Record& header)
  {
    for (size_t i = 0; i < col_stats.size(); ++i)
    {
      if (header[i].isEmpty())
        col_stats[i].name = boost::lexical_cast<std::string>(i);
      else
        col_stats[i].name.assign(header[i].str(), header[i].end());
    }
  }

  void fillColNamesWithNumbers()
  {
    for (size_t i = 0; i < col_stats.size(); ++i)
      col_stats[i].name = boost::lexical_cast<std::string>(i + 1);
  }

  //
  // JSON building
  //
  void buildJSONOutput(Jzon::Object& r) const
  {
    r.Add("version", 3);
    r.Add("data_type", "GENERAL");
    r.Add("size", (int)file_size);
    r.Add("data_rows", (int) valid_data_rows);
    r.Add("empty_rows", (int) empty_rows);
    r.Add("invalid_rows", (int) invalid_rows);
    r.Add("num_columns", (int) col_stats.size());
    r.Add("delimeter", delimiter);
    r.Add("with_header", has_header);

    addNames(r);
    addTypes(r);
    addClasses(r);
    addUniques(r);
    addLocked(r);
    addHistograms(r);
    addBins(r);
    addMeans(r);
    addStdev(r);
    addMins(r);
    addMaxes(r);
    addLastCol(r);
  }

  void addNames(Jzon::Object& p) const
  {
    Jzon::Array names;
    for (size_t i = 0; i < col_stats.size(); ++i)
      names.Add(col_stats[i].name);
    p.Add("names", names);
  }

  void addTypes(Jzon::Object& p) const
  {
    Jzon::Array types;
    for (size_t i = 0; i < col_stats.size(); ++i)
      types.Add(col_stats[i].getType());
    p.Add("dtypes", types);
  }

  void addClasses(Jzon::Object& p) const
  {
    using namespace ersatz::utils;

    Jzon::Array classes_list;
    for (size_t i = 0; i < col_stats.size(); ++i)
    {
      Jzon::Array classes;
      if (col_stats[i].hasClasses())
      {
        StrUnique::SortedCountMap sorted = col_stats[i].unique_values.getSortedCountMap();
        for (auto it = sorted.begin(); it != sorted.end(); ++it)
          classes.Add(it->first);
      }
      classes_list.Add(classes);
    }
    p.Add("classes", classes_list);
  }

  void addUniques(Jzon::Object& p) const
  {
    Jzon::Array uniques;
    for (size_t i = 0; i < col_stats.size(); ++i)
      uniques.Add((int) col_stats[i].unique_values.size());
    p.Add("uniques_per_col", uniques);
  }

  void addLocked(Jzon::Object& p) const
  {
    Jzon::Array locked;
    for (size_t i = 0; i < col_stats.size(); ++i)
      locked.Add(col_stats[i].isLocked());
    p.Add("locked", locked);
  }

  void addHistograms(Jzon::Object& p) const
  {
    using namespace ersatz::utils;

    Jzon::Array hist_list;
    for (size_t i = 0; i < col_stats.size(); ++i)
    {
      Jzon::Array hist;
      if (col_stats[i].hist)
      {
        Histogram<Float>::Counts c = col_stats[i].hist->getCounts();
        for (auto it = c.begin(); it != c.end(); ++it)
          hist.Add((int) *it);
      }
      hist_list.Add(hist);
    }
    p.Add("histogram", hist_list);
  }

  void addBins(Jzon::Object& p) const
  {
    using namespace ersatz::utils;

    Jzon::Array bin_list;
    for (size_t i = 0; i < col_stats.size(); ++i)
    {
      Jzon::Array bins;
      if (col_stats[i].hist)
      {
        Histogram<Float>::Values b = col_stats[i].hist->getBins();
        for (auto it = b.begin(); it != b.end(); ++it)
          bins.Add(*it);
      }
      bin_list.Add(bins);
    }
    p.Add("bins", bin_list);
  }

  void addMeans(Jzon::Object& p) const
  {
    using namespace ersatz::utils;

    Jzon::Array means;
    for (size_t i = 0; i < col_stats.size(); ++i)
    {
      if (col_stats[i].isNumeric())
        means.Add(col_stats[i].simple_stat.mean());
      else
        means.Add(Jzon::null);
    }
    p.Add("mean", means);
  }

  void addStdev(Jzon::Object& p) const
  {
    using namespace ersatz::utils;

    Jzon::Array stdevs;
    for (size_t i = 0; i < col_stats.size(); ++i)
    {
      if (col_stats[i].isNumeric())
        stdevs.Add(col_stats[i].simple_stat.stdev());
      else
        stdevs.Add(Jzon::null);
    }
    p.Add("stdev", stdevs);
  }

  void addMins(Jzon::Object& p) const
  {
    using namespace ersatz::utils;

    Jzon::Array mins;
    for (size_t i = 0; i < col_stats.size(); ++i)
    {
      if (col_stats[i].isNumeric())
        mins.Add(col_stats[i].simple_stat.min());
      else
        mins.Add(Jzon::null);
    }
    p.Add("min", mins);
  }

  void addMaxes(Jzon::Object& p) const
  {
    using namespace ersatz::utils;

    Jzon::Array maxes;
    for (size_t i = 0; i < col_stats.size(); ++i)
    {
      if (col_stats[i].isNumeric())
        maxes.Add(col_stats[i].simple_stat.max());
      else
        maxes.Add(Jzon::null);
    }
    p.Add("max", maxes);
  }

  void addLastCol(Jzon::Object& p) const
  {
    using namespace Jzon;

    Object lastcol;
    const ColStat& l = col_stats.back();

    lastcol.Add("min", col_stats.back().isNumeric() ? l.simple_stat.min() : 0);
    lastcol.Add("max", col_stats.back().isNumeric() ? l.simple_stat.max() : l.unique_values.size() - 1);
    lastcol.Add("unique", (int) l.unique_values.size());

    Object classes;
    Object distrib;
    if (l.lastColHasClasses())
    {
      bool isInt = l.isInt();
      ersatz::utils::StrUnique::SortedCountMap sorted = l.unique_values.getSortedCountMap();
      size_t n = 0;
      for (auto it = sorted.begin(); it != sorted.end(); ++it)
      {
        classes.Add( isInt ? formatAsInteger(it->first) : it->first, (int) it->second);
        n += it->second;
      }
      size_t i = 0;
      for (auto it = sorted.begin(); it != sorted.end(); ++it, ++i)
        distrib.Add(isInt ? formatAsInteger(it->first) : it->first, it->second / (double) n);
    }
    lastcol.Add("distrib", distrib);
    lastcol.Add("classes", classes);

    p.Add("last_column_info", lastcol);
  }

private:
  size_t valid_data_rows;
  size_t empty_rows;
  size_t invalid_rows;
  ColStats col_stats;
  bool has_header;
  std::string delimiter;
  mutable size_t log_messages;
  size_t file_size;
};

} // namespace stat
} // namespace ersatz

#endif // ERSATZ_DM_CSVStat_h
