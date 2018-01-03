#ifndef ERSATZ_UTILS_Unique_h
#define ERSATZ_UTILS_Unique_h

#include <map>
#include <vector>
#include <unordered_map>
#include <ersatz/utils/Error.h>
#include <ersatz/utils/String.h>

namespace ersatz
{
namespace utils
{

/**
 * Fast unique string detection with pre allocated memory.
 */
class StrUnique
{
public:
  typedef std::map<std::string, size_t> SortedCountMap;
  typedef std::unordered_map<StrRef, size_t, StrRefHash, StrRefEqual> CountMap;

public:
  StrUnique(size_t _max_uniques = 1000, size_t max_mem = 64 * 1024 /*64K*/) :
      max_uniques(_max_uniques), buf(max_mem)
  {
    counts.reserve(_max_uniques);
    reset();
  }

  void reset()
  {
    buf_pos = buf.data();
    mem_left = buf.size();
    counts.clear();
    full = false;
  }

  void add(const StrRef& x)
  {
    if (full)
      return;

    CountMap::iterator it = counts.find(x);
    if (it != counts.end())
    {
      it->second++;
      return;
    }

    // insert new item
    size_t l = x.len();
    if (l > mem_left)
    {
      // out of memory
      full = true;
      return;
    }

    // insert new item with count=1
    memcpy(buf_pos, x.str(), l);
    counts[StrRef(buf_pos, buf_pos + l)] = 1;
    buf_pos += l;
    mem_left -= l;
    if (counts.size() == max_uniques)
      full = true;
  }

  void remove(const StrRef& x)
  {
    CountMap::iterator it = counts.find(x);
    if (it != counts.end())
    {
      if (it->second > 0)
        it->second--;
      if (it->second == 0)
        counts.erase(it);
    }
  }

  inline bool isFull() const
  {
    return full;
  }

  inline size_t size() const
  {
    return counts.size();
  }

  void removeAll(const StrRef& x)
  {
    counts.erase(x);
  }

  SortedCountMap getSortedCountMap() const
  {
    SortedCountMap ret;
    for (auto it = counts.begin(); it != counts.end(); ++it)
      ret.insert(SortedCountMap::value_type(std::string(it->first.str(), it->first.end()), it->second));
    return ret;
  }

  const CountMap& getCountMap() const
  {
    return counts;
  }

private:
  typedef std::vector<char> Buffer;

private:
  size_t max_uniques;
  Buffer buf;
  char * buf_pos;
  size_t mem_left;
  CountMap counts;
  bool full;
};

} // namespace utils
} // namespace ersatz

#endif // ERSATZ_UTILS_Unique_h
