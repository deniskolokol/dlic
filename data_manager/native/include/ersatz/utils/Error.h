#ifndef ERSATZ_UTILS_Error_h
#define ERSATZ_UTILS_Error_h

#include <stdexcept>
#include <string>
#include <boost/current_function.hpp>
#include <boost/static_assert.hpp>
#include <iostream>
#include <cstring>
#include <sstream>

namespace ersatz
{
namespace utils
{

void logJSON(const Jzon::Object& o)
{
  using namespace Jzon;
  Writer writer(o, NoFormat);
  writer.Write();
  std::cerr << writer.GetResult() << std::endl;
}

void logUserError(const std::string& msg)
{
  using namespace Jzon;
  Object r;
  r.Add("status", "FATAL");
  r.Add("descr", msg);
  logJSON(r);
}

void logFatalError(const std::string& msg, const std::string& debug = "")
{
  using namespace Jzon;
  Object r;
  r.Add("status", "FATAL INTERNAL");
  r.Add("descr", msg);
  r.Add("debug", debug);
  logJSON(r);
}

class Exception: public std::logic_error
{
public:
  explicit Exception(const std::string& _debug_info, const std::string& message = "") :
      std::logic_error(message), debug_info(_debug_info)
  {
  }
  virtual ~Exception() throw ()
  {
  }
  virtual const std::string& debugInfo() const
  {
    return debug_info;
  }
protected:
  std::string debug_info;
};

class UserException: public Exception
{
public:
  explicit UserException(const std::string& _debug_info, const std::string& message) :
      Exception(_debug_info, message)
  {
  }
  virtual ~UserException() throw ()
  {
  }
};

inline std::string formatDebugInfo(const char* cond, const char* file, unsigned int line, const char *func)
{
  std::ostringstream errmsg;
  errmsg << "************** Debug Info **************" << std::endl;
  errmsg << "  file: " << file << std::endl;
  errmsg << "  line: " << line << std::endl;
  char const *pCurly = strchr(func, '(');
  if (pCurly)
    errmsg << "  function: " << std::string(func, pCurly) << std::endl;
  else
    errmsg << "  function: " << func << std::endl;
  if (cond != 0)
  {
    errmsg << "  cause: " << cond << " does not hold" << std::endl;
  }
  return errmsg.str();
}

#define E_USER_ASSERT( cond, details ) \
  if (!(cond)) \
  {\
    throw ersatz::utils::UserException( ersatz::utils::formatDebugInfo(#cond, __FILE__, __LINE__, BOOST_CURRENT_FUNCTION), details ); \
  }

#define E_USER_FAIL( details ) throw ersatz::utils::UserException( ersatz::utils::formatDebugInfo(0, __FILE__, __LINE__, BOOST_CURRENT_FUNCTION), details );

#define E_ASSERT( cond ) \
  if (!(cond)) \
  {\
    throw ersatz::utils::Exception( ersatz::utils::formatDebugInfo(#cond, __FILE__, __LINE__, BOOST_CURRENT_FUNCTION) ); \
  }

#define E_ASSERT_EXT( cond, details ) \
  if (!(cond)) \
  {\
    throw ersatz::utils::Exception( ersatz::utils::formatDebugInfo(#cond, __FILE__, __LINE__, BOOST_CURRENT_FUNCTION), details ); \
  }

#define E_FAIL throw ersatz::utils::Exception( ersatz::utils::formatDebugInfo(0, __FILE__, __LINE__, BOOST_CURRENT_FUNCTION) );

} // namespace utils
} // namespace ersatz

#endif // ERSATZ_UTILS_Error_h
