#ifndef ERSATZ_DM_Filter_h
#define ERSATZ_DM_Filter_h

#include <ersatz/dm/Common.h>

namespace ersatz
{
namespace dm
{

class RecordSource: private boost::noncopyable
{
public:
  virtual ~RecordSource()
  {
  }

  /**
   * Request n records. Returns a matrix with at most n records.
   * Returns true if there is valid data in mtx false if no data and end of stream has been reached.
   */
  virtual bool getNext(size_t n, FMtx& records) = 0;

  /**
   * Returns the total number of records.
   */
  virtual size_t getSize() = 0;
};

typedef std::shared_ptr<RecordSource> SPRecordSource;
typedef std::vector<SPRecordSource> SPRecordSourceVec;

class NoTranform: public RecordSource
{
public:
  NoTranform(RecordSource& _src)
      : src(_src)
  {
  }

  virtual bool getNext(size_t n, FMtx& records)
  {
    return src.getNext(n, records);
  }

  virtual size_t getSize()
  {
    return src.getSize();
  }
private:
  RecordSource& src;
};

class SimpleShuffle: public RecordSource
{
public:
  SimpleShuffle(RecordSource& _src)
      : src(_src)
  {
  }

  virtual bool getNext(size_t n, FMtx& records)
  {
    if (!src.getNext(n, records))
      return false;
    std::random_shuffle(records.begin(), records.end());
    return true;
  }

  virtual size_t getSize()
  {
    return src.getSize();
  }
private:
  RecordSource& src;
};

class UnderSampler: public RecordSource
{
public:
  UnderSampler(RecordSource& _src, size_t _out_ind, CountVec counts, size_t _buf_size = 1000 )
      : src(_src), out_ind(_out_ind), returned(counts.size(), 0), buf_size(_buf_size)
  {
    min = *std::min_element( counts.begin()+1, counts.end() );
    size = min * (counts.size() - 1);
  }

  virtual size_t getSize()
  {
    return size;
  }

  virtual bool getNext(size_t n, FMtx& records)
  {
    records.clear();
    if( !src.getNext(buf_size,tmp) )
      return false;

    for( FVec& r: tmp )
    {
      size_t c = r[out_ind];
      if( returned[c] < min )
      {
        records.push_back(r);
        returned[c]++;
      }
    }

    return true;
  }
private:
  RecordSource& src;
  size_t out_ind;
  size_t min;
  CountVec returned;
  size_t size;
  size_t buf_size;
  FMtx tmp;
};

class OverSampler: public RecordSource
{
public:
  OverSampler(RecordSource& _src, size_t _out_ind, CountVec counts, size_t _buf_size = 1000 )
      : src(_src), out_ind(_out_ind), multiplier(counts.size()), class_counter(counts.size(),0), class_counter_threshold(counts.size()), buf_size(_buf_size)
  {
    max = *std::max_element( counts.begin()+1, counts.end() );
    size = max * (counts.size() - 1);

    for( size_t i=1; i<counts.size(); ++i )
    {
      double m = max / (double)counts[i];
      multiplier[i] = trunc(m);
      class_counter_threshold[i] = counts[i] - (max - counts[i] * multiplier[i]);
    }
  }

  virtual size_t getSize()
  {
    return size;
  }

  virtual bool getNext(size_t n, FMtx& records)
  {
    records.clear();
    if( !src.getNext(buf_size,tmp) )
      return false;

    for( FVec& r: tmp )
    {
      size_t c = r[out_ind];
      if( c==0 )
        continue;

      size_t l = class_counter[c] < class_counter_threshold[c] ? multiplier[c] : multiplier[c] + 1;
      for(size_t i=0; i<l; ++i)
        records.push_back(r);

      class_counter[c]++;
    }

    return true;
  }
private:
  RecordSource& src;
  size_t out_ind;
  size_t max;
  CountVec multiplier;
  CountVec class_counter;
  CountVec class_counter_threshold;
  size_t size;
  size_t buf_size;
  FMtx tmp;
};

class UniformSampler: public RecordSource
{
public:
  UniformSampler(RecordSource& _src, size_t _out_ind, CountVec counts, size_t _buf_size = 1000 )
      : src(_src), out_ind(_out_ind), multiplier(counts.size()), class_counter(counts.size(),0), class_counter_threshold(counts.size()), buf_size(_buf_size)
  {
    size = src.getSize();

    // mindenkire meghatarozzuk hany mintaja legyen
    // - ahol novelni kell a szamot ott ugyanazt csinaljuk mint az oversampernel
    // - ahol eldobalni kell elhagyjuk az utolsokat (majd finomitjuk)

    max = *std::max_element( counts.begin()+1, counts.end() );
    size = max * (counts.size() - 1);

    for( size_t i=1; i<counts.size(); ++i )
    {
      double m = max / (double)counts[i];
      multiplier[i] = trunc(m);
      class_counter_threshold[i] = counts[i] - (max - counts[i] * multiplier[i]);
    }
  }

  virtual size_t getSize()
  {
    return size;
  }

  virtual bool getNext(size_t n, FMtx& records)
  {
    records.clear();
    if( !src.getNext(buf_size,tmp) )
      return false;

    for( FVec& r: tmp )
    {
      size_t c = r[out_ind];
      if( c==0 )
        continue;

      size_t l = class_counter[c] < class_counter_threshold[c] ? multiplier[c] : multiplier[c] + 1;
      for(size_t i=0; i<l; ++i)
        records.push_back(r);

      class_counter[c]++;
    }

    return true;
  }
private:
  RecordSource& src;
  size_t out_ind;
  size_t max;
  CountVec multiplier;
  CountVec class_counter;
  CountVec class_counter_threshold;
  size_t size;
  size_t buf_size;
  FMtx tmp;
};


class Split: public RecordSource
{
public:
  Split(RecordSource& _src, size_t start, size_t end)
      : src(_src)
  {
    E_ASSERT(end > start);

    size_t n = src.getSize();

    first = (size_t) (n * (start / 100.0));
    last = (size_t) (n * (end / 100.0));
    pos = 0;
  }

  virtual size_t getSize()
  {
    return 0; // TODO src.getSize()
  }

  virtual bool getNext(size_t n, FMtx& records)
  {
    if (pos < first)
    {
      size_t chunk_size = 1000;
      size_t skip_chunks = first / chunk_size;
      size_t skip = first % chunk_size;
      FMtx temp;
      for (size_t i = 0; i < skip_chunks; ++i)
      {
        if (!src.getNext(chunk_size, temp))
          return false;
        pos += temp.size();
      }
      if (!src.getNext(skip, temp))
        return false;
      pos += temp.size();
    }

    if (pos >= last)
      return false;

    size_t m = std::min(n, last - pos);
    if (!src.getNext(m, records))
      return false;

    pos += records.size();
    return true;
  }
private:
  RecordSource& src;
  size_t pos, first, last;
};

} // namespace dm
} // namespace ersatz

#endif // ERSATZ_DM_Filter_h
