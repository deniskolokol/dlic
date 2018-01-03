#ifndef ERSATZ_UTILS_Histogram_h
#define ERSATZ_UTILS_Histogram_h

#include <vector>
#include <ersatz/utils/Error.h>

namespace ersatz
{
namespace utils
{

inline size_t heuristicBinCount(size_t n)
{
  size_t lo = std::min<size_t>(n, 10);
  size_t hi = std::min<size_t>(n, 100);
  size_t bc = (hi * hi * hi) / 10000;
  if (bc < lo)
    bc = lo;
  if (bc > hi)
    bc = hi;
  return bc;
}

template<typename T>
class Histogram
{
public:
  typedef T Value;
  typedef std::vector<Value> Values;
  typedef std::vector<size_t> Counts;
public:
  Histogram(Value _min, Value _max, size_t _bins = 10) :
      m_min(_min), m_max(_max), m_binSize(0), m_counts(_bins, 0)
  {
    E_ASSERT(m_min <= m_max);
    E_ASSERT(m_counts.size() > 0);
    if (m_max > m_min)
      m_binSize = (m_max - m_min) / m_counts.size();
    else
      m_binSize = 1.0; // can be anything but 0
  }
public:
  const Value& getMin() const
  {
    return m_min;
  }
  const Value& getMax() const
  {
    return m_max;
  }
  const Counts& getCounts() const
  {
    return m_counts;
  }
  // _bins+1 value, starts by _min, ends by _max
  Values getBins() const
  {
    Values bins(m_counts.size() + 1);
    for (size_t i = 0; i < m_counts.size(); ++i)
      bins[i] = m_min + i * m_binSize;
    bins[m_counts.size()] = m_max;
    return bins;
  }
public:
  void add(const T& x)
  {
    ++m_counts[getBin(x)];
  }
  void add(const T& x, int k)
  {
    m_counts[getBin(x)] += k;
  }

public:
  /*template<typename It>
   void add(It it, const It& ite)
   {
   for (; it != ite; ++it)
   add(*it);
   }*/
private:
  inline size_t getBin(const Value& v) const
  {
    size_t bin = (v - m_min) / m_binSize;
    if (bin >= m_counts.size())
      bin = m_counts.size() - 1;
    return bin;
  }
private:
  Value m_min;
  Value m_max;
  Value m_binSize;
  Counts m_counts;
};

} // namespace utils
} // namespace ersatz

#endif // ERSATZ_UTILS_Histogram_h
