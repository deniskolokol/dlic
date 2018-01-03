#ifndef ERSATZ_UTILS_SimpleStat_h
#define ERSATZ_UTILS_SimpleStat_h

#include <vector>
#include <ersatz/utils/Error.h>

namespace ersatz
{
namespace utils
{

/**
 * Calculate simple statistics online: min, max, mean, variance.
 */
template<typename T>
class SimpleStat
{
public:
  void reset()
  {
    m_min = std::numeric_limits < T > ::max();
    m_max = -std::numeric_limits < T > ::max();
    n = 0;
    _mean = 0;
    M2 = 0;
  }

  void add(T x)
  {
    // min, max
    if (x < m_min)
      m_min = x;
    if (x > m_max)
      m_max = x;

    // online calculateion of avg and variance
    // based on the numarically stable algorithm provided by Knuth
    // http://en.wikipedia.org/wiki/Algorithms_for_calculating_variance#Incremental_algorithm)
    ++n;
    T delta = x - _mean;
    _mean += delta / n;
    M2 += delta * (x - _mean);
  }

  inline T min() const
  {
    return m_min;
  }

  inline T max() const
  {
    return m_max;
  }

  inline T mean() const
  {
    return _mean;
  }

  inline T variance() const
  {
    return n > 1 ? M2 / (n - 1) : 0;
  }

  inline T stdev() const
  {
    return sqrt(variance());
  }
private:
  T m_min, m_max, _mean, M2;
  size_t n;
};

}
// namespace utils
}// namespace ersatz

#endif // ERSATZ_UTILS_SimpleStat_h
