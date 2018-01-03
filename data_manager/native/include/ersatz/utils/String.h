#ifndef ERSATZ_UTILS_String_h
#define ERSATZ_UTILS_String_h

#include <cmath>
#include <string>
#include <boost/cstdint.hpp>
#include <ersatz/utils/Error.h>

namespace ersatz
{
namespace utils
{

/**
 * Represents reference for a string part.
 *
 * Warning: it does not manage memory so the user have to make sure the underlying string is valid.
 */
class StrRef
{
public:
  StrRef()
  {
    null();
  }

  StrRef(const char * str, const char * end)
  {
    assign(str, end);
  }

  StrRef(const char * str, size_t len)
  {
    assign(str, len);
  }

  void null()
  {
    m_str = 0;
    m_end = 0;
  }

  void assign(const char * str, const char * end)
  {
    m_str = str;
    m_end = end;
  }

  void assign(const char * str, size_t len)
  {
    m_str = str;
    m_end = str + len;
  }

  inline bool isNull() const
  {
    return m_str == 0;
  }

  inline bool isEmpty() const
  {
    return m_str == m_end;
  }

  inline size_t len() const
  {
    return m_end - m_str;
  }

  inline const char * str() const
  {
    return m_str;
  }

  inline const char * end() const
  {
    return m_end;
  }

private:
  const char * m_str;
  const char * m_end;
};

inline bool operator==(const StrRef& a, const StrRef& b)
{
  return a.len() == b.len() && strncmp(a.str(), b.str(), a.len()) == 0;
}

inline bool operator==(const StrRef& a, const std::string& b)
{
  return a.len() == b.size() && strncmp(a.str(), b.c_str(), a.len()) == 0;
}

inline bool operator==(const std::string& a, const StrRef& b)
{
  return b == a;
}

/**
 * Fast 64 bit string hash. (There are slighty better ones but this is small:)
 */
uint64_t MurmurHash64A(const void * key, int len, unsigned int seed = 0)
{
  static const uint64_t m = 0xc6a4a7935bd1e995;
  static const int r = 47;

  uint64_t h = seed ^ (len * m);

  const uint64_t * data = (const uint64_t *) key;
  const uint64_t * end = data + (len / 8);

  while (data != end)
  {
    uint64_t k = *data++;

    k *= m;
    k ^= k >> r;
    k *= m;

    h ^= k;
    h *= m;
  }

  const unsigned char * data2 = (const unsigned char*) data;

  switch (len & 7)
  {
  case 7:
    h ^= uint64_t(data2[6]) << 48;
  case 6:
    h ^= uint64_t(data2[5]) << 40;
  case 5:
    h ^= uint64_t(data2[4]) << 32;
  case 4:
    h ^= uint64_t(data2[3]) << 24;
  case 3:
    h ^= uint64_t(data2[2]) << 16;
  case 2:
    h ^= uint64_t(data2[1]) << 8;
  case 1:
    h ^= uint64_t(data2[0]);
    h *= m;
  };

  h ^= h >> r;
  h *= m;
  h ^= h >> r;

  return h;
}

struct StrRefEqual: std::binary_function<StrRef, StrRef, bool>
{
  bool operator()(const StrRef& x, const StrRef& y) const
  {
    if (x.len() != y.len())
      return false;
    return std::equal(x.str(), x.end(), y.str());
  }
};

struct StrRefHash: std::unary_function<StrRef, size_t>
{
  size_t operator()(const StrRef& s) const
  {
    return MurmurHash64A(s.str(), s.len());
  }
};

/**
 * Fast real number parser for zero terminated strings. Leading and traling spaces are valid.
 *
 */
template<typename T>
inline bool parseReal(T & num, const char *p)
{
  num = 0.0;
  int digits = 0;

  // skip leading spaces
  while (*p == ' ')
    ++p;

  // handle sign
  bool neg = false;
  if (*p == '-')
  {
    neg = true;
    ++p;
  }
  else if (*p == '+')
  {
    neg = false;
    ++p;
  }

  // get the digits before decimal point
  while (isdigit(*p))
  {
    num = (num * 10.0) + (*p - '0');
    ++p;
    ++digits;
  }

  // get the digits after decimal point
  if (*p == '.')
  {
    T f = 0.0;
    T scale = 1.0;
    ++p;
    while (isdigit(*p))
    {
      f = (f * 10.0) + (*p - '0');
      ++p;
      scale *= 10.0;
      ++digits;
    }
    num += f / scale;
  }

  // we must have some digits now
  if (digits == 0)
    return false;

  // get the digits after the "e"/"E" (exponenet)
  if (*p == 'e' || *p == 'E')
  {
    int e = 0;
    bool neg_e = false;
    ++p;
    if (*p == '-')
    {
      neg_e = true;
      ++p;
    }
    else if (*p == '+')
    {
      neg_e = false;
      ++p;
    }

    // get exponent
    digits = 0;
    while (isdigit(*p))
    {
      e = (e * 10) + (*p - '0');
      ++p;
      ++digits;
    }
    if (digits == 0)
      return false;
    if (neg_e)
      e = -e;
    if (e > std::numeric_limits < T > ::max_exponent10)
      return false;
    else if (e < std::numeric_limits < T > ::min_exponent10)
      return false;

    // apply exponent
    num *= pow( 10, e );
  }

  // skip post whitespaces
  while (*p == ' ')
    ++p;

  if (*p != '\0')
    return false;

  // apply sign to number
  if (neg)
    num = -num;

  return true;
}

/**
 * Fast real number parser for string references.
 */
template<typename T>
inline bool parseReal(T & num, const StrRef& str)
{
  if (str.isNull())
    return false;
  char * e = const_cast<char*>(str.end());  // Warning: unsafe! It assumes end() is writeable! (but it is true for all normal cases)
  char c = *e;
  *e = 0;
  bool r = parseReal(num, str.str());
  *e = c;
  return r;
}

} // namespace utils
} // namespace ersatz

#endif // ERSATZ_UTILS_String_h
