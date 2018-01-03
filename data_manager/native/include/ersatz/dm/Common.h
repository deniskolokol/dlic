#ifndef ERSATZ_DM_Common_h
#define ERSATZ_DM_Common_h

#include <vector>
#include <set>
#include <ersatz/utils/Error.h>

namespace ersatz
{
namespace dm
{

typedef double Float;
typedef std::vector<Float> FVec;
typedef std::vector<FVec> FMtx;
typedef std::vector<size_t> IndexVec;
typedef std::vector<size_t> CountVec;
typedef std::set<std::string> StrSet;
typedef std::map<std::string, size_t> CountMap;
typedef std::map<std::string, size_t> IndexMap;

//
// DM specific Loging
//
// TODO: think over the while logging and error handling
//

void log(const Jzon::Object& r)
{
  static size_t log_messages = 0;
  log_messages++;
  if (log_messages < 1000)
    ersatz::utils::logJSON(r);
}

void report(const std::string& msg)
{
  using namespace Jzon;
  Object r;
  r.Add("status", "INFO");
  r.Add("descr", msg);
  log(r);
}

void reportDataError(int row, int col)
{
  using namespace Jzon;
  Object r;
  r.Add("status", "DATA");
  Jzon::Array c;
  c.Add(row);
  c.Add(col);
  r.Add("descr", c);
  log(r);
}


} // namespace dm
} // namespace ersatz

#endif // ERSATZ_DM_Common_h
