#ifndef ERSATZ_DM_ColumnStat_h
#define ERSATZ_DM_ColumnStat_h

#include <ersatz/dm/Common.h>

namespace ersatz
{
namespace dm
{

enum ColType
{
  Numeric,      // number (can be int or float)
  Categorical,  // string with less than 100 unique values
  Other
};

/**
 * Represents a column of a tabular dataset.
 */

/*class ColumnStat
{
public:


private:
  ColType type;

  std::set<std::string> strings;
  size_t string_num;
  size_t num_num;
  std::string name;
  ersatz::utils::StrUnique unique_values;
  SPHist hist;
  ersatz::utils::SimpleStat<Float> simple_stat;


};*/

} // namespace dm
} // namespace ersatz

#endif // ERSATZ_DM_ColumnStat_h
