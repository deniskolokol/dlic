#ifndef ERSATZ_DM_ColumnEncoder_h
#define ERSATZ_DM_ColumnEncoder_h

#include <string>
#include <set>
#include <map>
#include <ersatz/dm/Common.h>
#include <ersatz/dm/ColumnStat.h>

namespace ersatz
{
namespace dm
{

/*
 * Interface for column encoders. A colunmn encoder can encode a string value of the text input to float number(s) for the training.
 * Typically numbers are encoded by converting the text to float and apply normalization.
 * Categorical fileds are encoded as a binary vector where only the category of the current value gets 1 all others are 0.
 */
class ColumnEncoder
{
public:
  virtual ~ColumnEncoder()
  {
  }

  /**
   * Retruns how many numbers are needed to encode this value.
   */
  virtual size_t getEncodedSize() const = 0;

  /**
   * Encode the value starting from the position pointed by it. Warning: caller should ensure there is enough room after it!
   * Iterator will be moved to pass the encoded block.
   * If encode failes it returns false, in this case iterator value is not defined (it can be moved or left as it is)
   */
  virtual bool encode(const ersatz::utils::StrRef& str, FVec::iterator& it) const = 0;
};

class IgnoreColumnEnoder: public ColumnEncoder
{
public:
  virtual size_t getEncodedSize() const
  {
    return 0;
  }

  virtual bool encode(const ersatz::utils::StrRef& str, FVec::iterator&) const
  {
    return true;
  }
};

/*
 * Encode everything with a zero. (e.g.: for columns with zero variance)
 */

class NullColumnEnoder: public ColumnEncoder
{
public:
  virtual size_t getEncodedSize() const
  {
    return 1;
  }

  virtual bool encode(const ersatz::utils::StrRef& str, FVec::iterator& it) const
  {
    *it = 0;
    ++it;
    return true;
  }
};

/*
 * Encode numbers. It does not scale numbers and substitute missing values with mean.
 */

class NumColumnEnoder: public ColumnEncoder
{
public:
  NumColumnEnoder(Float _mean)
      : mean(_mean)
  {
  }

  virtual size_t getEncodedSize() const
  {
    return 1;
  }

  virtual bool encode(const ersatz::utils::StrRef& str, FVec::iterator& it) const
  {
    if (str.isEmpty())  // N/A value
    {
      *it++ = mean;
      return true;
    }

    Float x;
    if (!ersatz::utils::parseReal(x, str))
      return false;

    *it++ = x;
    return true;
  }
private:
  Float mean;
};

/*
 * Encode numbers with simple min-max normalization. N/A values are substituted with the mean. Numbers are normalized to 0-1.
 */

class NumColumnEnoderWithMinMax: public ColumnEncoder
{
public:
  NumColumnEnoderWithMinMax(Float _min, Float _max, Float _mean)
      : min(_min), d(_max - _min), null_val((_mean - min) / d)
  {
    E_ASSERT(_max > _min);
    E_ASSERT(_mean >= _min);
    E_ASSERT(_mean <= _max);
  }

  virtual size_t getEncodedSize() const
  {
    return 1;
  }

  virtual bool encode(const ersatz::utils::StrRef& str, FVec::iterator& it) const
  {
    if (str.isEmpty()) // N/A value
    {
      *it++ = null_val;
      return true;
    }

    Float x;
    if (!ersatz::utils::parseReal(x, str))
      return false;

    *it++ = (x - min) / d;
    return true;
  }
private:
  Float min, d, null_val;
};

/*
 * Encode numbers with standard score normalization. N/A values are substituted with the 0 (means's std score is 0). Numbers are normalized with the standard score.
 * see http://en.wikipedia.org/wiki/Standard_score
 */
class NumColumnEnoderWithStdScore: public ColumnEncoder
{
public:
  NumColumnEnoderWithStdScore(Float _mean, Float _stdev)
      : mean(_mean), stdev(_stdev)
  {
    E_ASSERT(stdev > 0);
  }

  virtual size_t getEncodedSize() const
  {
    return 1;
  }

  virtual bool encode(const ersatz::utils::StrRef& str, FVec::iterator& it) const
  {
    if (str.isEmpty()) // N/A value
    {
      *it = 0;
      ++it;
      return true;
    }

    Float x;
    if (!ersatz::utils::parseReal(x, str))
      return false;

    *it = (x - mean) / stdev;
    ++it;
    return true;
  }
private:
  Float mean, stdev;
};

/**
 * Encode categorical fields with binary representation.
 */
class CategoricalColumnEncoder: public ColumnEncoder
{
public:
  CategoricalColumnEncoder(const StrSet& values)
  {
    size_t i = 0;
    for (auto& v : values)
      index_map[v] = i++;
    n = index_map.size();
  }

  virtual size_t getEncodedSize() const
  {
    return n;
  }

  virtual bool encode(const ersatz::utils::StrRef& str, FVec::iterator& it) const
  {
    static std::string s;

    std::fill(it, it + n, 0);
    if (str.isEmpty())
    {
      it += n;
      return true;
    }

    s.assign(str.str(), str.end());
    IndexMap::const_iterator i = index_map.find(s);
    if (i == index_map.end())
      return false;

    it[i->second] = 1.0;
    it += n;
    return true;
  }
private:
  typedef std::map<std::string, size_t> IndexMap;
private:
  size_t n;
  IndexMap index_map;
};

/**
 * Encode categorical fields with indexes (1 based index, 0 means missing value)
 */
class IndexColumnEncoder: public ColumnEncoder
{
public:
  IndexColumnEncoder(const StrSet& values)
  {
    size_t i = 0;
    for (auto& v : values)
      index_map[v] = i++;
    n = index_map.size();
  }

  virtual size_t getEncodedSize() const
  {
    return 1;
  }

  virtual bool encode(const ersatz::utils::StrRef& str, FVec::iterator& it) const
  {
    static std::string s;

    if (str.isEmpty())
    {
      *it = 0;
      it++;
      return true;
    }

    s.assign(str.str(), str.end());
    IndexMap::const_iterator i = index_map.find(s);
    if (i == index_map.end())
      return false;

    *it = i->second+1;
    it++;
    return true;
  }
private:
  size_t n;
  IndexMap index_map;
};


/**
 * Encode binary fields.
 */
class BinaryColumnEncoder: public ColumnEncoder
{
public:
  BinaryColumnEncoder(const std::string& _val1, const std::string& _val2)
      : val1(_val1), val2(_val2)
  {
  }

  virtual size_t getEncodedSize() const
  {
    return 1;
  }

  virtual bool encode(const ersatz::utils::StrRef& str, FVec::iterator& it) const
  {
    if (str.isEmpty())
    {
      *it = 0.5;
      ++it;
      return true;
    }

    if (str == val1)
      *it = 0;
    else if (str == val2)
      *it = 1;
    else
      return false;

    ++it;
    return true;
  }
private:
  const std::string val1;
  const std::string val2;
};

/**
 * Encode integers with binary representation.
 */
class IntegerColumnEncoder: public ColumnEncoder
{
public:
  IntegerColumnEncoder(int _min, int _max) : min(_min), max(_max)
  {
    n = max - min;
    //std::cout << "IntegerColumnEncoder" << min << "," << max << std::endl;
  }

  virtual size_t getEncodedSize() const
  {
    return n;
  }

  virtual bool encode(const ersatz::utils::StrRef& str, FVec::iterator& it) const
  {
    std::fill(it, it + n, 0);
    if (str.isEmpty())
    {
      it += n;
      return true;
    }

    Float x;
    if (!ersatz::utils::parseReal(x, str))
      return false;

    if( x>min )
      it[x-min-1] = 1.0;
    it += n;
    return true;
  }
private:
  size_t n;
  int min, max;
};


typedef std::shared_ptr<ColumnEncoder> SPColumnEncoder;

/**
 * Factory functions for creating column encoders.
 */
ColumnEncoder * createNumericColumnEncoder(const FieldInfo& f, NormalizationType nt )
{
  if( f.stdev == 0 || f.min == f.max )
    return new IgnoreColumnEnoder();

  if( nt == NT_StdScore )
    return new NumColumnEnoderWithStdScore(f.mean, f.stdev );
  else if( nt == NT_MinMax )
    return new NumColumnEnoderWithMinMax(f.min, f.max, f.mean);
  else
    return new NumColumnEnoder(f.mean);
}

ColumnEncoder * createColumnEncoder(const FieldInfo& f, NormalizationType nt)
{
  if (f.encoding == ENC_Ignore )
    return new IgnoreColumnEnoder();

  if( f.encoding == ENC_Float )
    return createNumericColumnEncoder(f, nt);

  // permute
  if( f.output )
  {
    // do not permute output
    return new IndexColumnEncoder(f.classes);
  }
  else
  {
    // permute
    if (f.classes.size() == 2) // binary feature
    {
      auto it = f.classes.begin();
      std::string val1 = *it;
      it++;
      std::string val2 = *it;
      return new BinaryColumnEncoder(val1, val2);
    }
    else
    {
      if( f.is_int )
        return new IntegerColumnEncoder(f.min, f.max);
      else
        return new CategoricalColumnEncoder(f.classes);
    }
  }
}

} // namespace dm
} // namespace ersatz

#endif // ERSATZ_DM_ColumnStat_h
