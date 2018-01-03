#ifndef ERSATZ_DM_LoadConfig_h
#define ERSATZ_DM_LoadConfig_h

#include <map>
#include <vector>
#include <ersatz/dm/Common.h>
#include <Jzon.h>

namespace ersatz
{
namespace dm
{

enum NormalizationType
{
  NT_None = 0,
  NT_MinMax = 1,
  NT_StdScore = 2
};

enum BalancingType
{
  BT_None = 0,
  BT_Uniform = 1,
  BT_Undersample = 2,
  BT_Oversample = 3
};

enum Encoding
{
  ENC_Float,
  ENC_Permute,
  ENC_PermuteInt,
  ENC_Ignore
};

struct FieldInfo
{
  FieldInfo()
      : output(false), encoding(ENC_Float), mean(0), stdev(0), min(0), max(0), is_int(false)
  {
  }

  bool doPermute()
  {
    return encoding == ENC_Permute || encoding == ENC_PermuteInt;
  }

  bool output;
  Encoding encoding;
  double mean, stdev, min, max;
  StrSet classes;
  bool is_int;
};

typedef std::vector<FieldInfo> FieldInfos;

class LoadConfig
{
public:
  LoadConfig()
      : norm(NT_None), balancing(BT_None), shuffle(false), split(false)
  {
  }

  void load(const char * file_name)
  {
    using namespace Jzon;

    Object r;
    E_ASSERT(Jzon::FileReader::ReadFile(file_name, r));

    if( r.Has("version") )
      version = r.Get("version").AsValue().ToString();

    // parse field info (type, mean, stdev)
    Array &types = r.Get("dtypes").AsArray();
    Array &mean = r.Get("mean").AsArray();
    Array &stdev = r.Get("stdev").AsArray();
    Array &min = r.Get("min").AsArray();
    Array &max = r.Get("max").AsArray();
    Array &classes = r.Get("classes").AsArray();

    size_t cols = types.GetCount();
    E_ASSERT( mean.GetCount() == cols );
    E_ASSERT( stdev.GetCount() == cols );
    E_ASSERT( min.GetCount() == cols );
    E_ASSERT( max.GetCount() == cols );
    E_ASSERT( classes.GetCount() == cols );

    field_infos.clear();
    for( size_t i=0; i<cols; ++i )
    {
      FieldInfo f;
      for( auto& c: classes.Get(i).AsArray() )
        f.classes.insert(c.ToString());
      std::string type = types.Get(i).AsValue().ToString();
      if( type == "S" )
        f.encoding = ENC_Permute;
      else if( type=="-" )
        f.encoding = ENC_Ignore;
      else
      {
        f.encoding = ENC_Float;
        f.mean = mean.Get(i).ToDouble();
        f.stdev = stdev.Get(i).ToDouble();
        f.min = min.Get(i).ToDouble();
        f.max = max.Get(i).ToDouble();
        f.is_int = (type=="i");
      }
      field_infos.push_back(f);
    }

    // parse filters
    balancing = BT_None;
    size_t out_num = 0;
    size_t last_output = 0;
    Array &filters = r.Get("filters").AsArray();
    for (Jzon::Array::iterator it = filters.begin(); it != filters.end(); ++it)
    {
      E_ASSERT((*it).IsObject());
      Object& o = (*it).AsObject();
      std::string type;
      try
      {
        type = o.Get("name").ToString();
      }
      catch (...)
      {
        continue;
      }

      if (type == "ignore")
      {
        for (auto c : getColumns(o))
          field_infos[c].encoding = ENC_Ignore;
      }
      else if (type == "outputs")
      {
        for( auto c : getColumns(o))
        {
          field_infos[c].output = true;
          last_output = c;
          out_num++;
        }
      }
      else if (type == "balance")
      {
        std::string bt = o.Get("sample").ToString();
        if( bt == "undersampling")
          balancing = BT_Undersample;
        else if( bt == "oversampling" )
          balancing = BT_Oversample;
        else if( bt == "uniform")
          balancing = BT_Uniform;
      }
      else if (type == "permute")
      {
        for( auto c : getColumns(o))
          field_infos[c].encoding = ENC_Permute;
      }
      else if (type == "normalize")
      {
        norm = NT_MinMax; // or could be NT_StdScore;
      }
      else if (type == "shuffle")
      {
        shuffle = true;
      }
      else if (type == "merge")
      {
      }
      else if (type == "split")
      {
        split_start = boost::lexical_cast<double>(o.Get("start").ToString());
        split_end = boost::lexical_cast<double>(o.Get("end").ToString());
        split = true;
      }
    }

    if( out_num != 1 || !(field_infos[last_output].doPermute()) )
      balancing = BT_None;

    // output class counts for balancing
    if( balancing != BT_None )
    {
      Object &output_classes = r.Get("output_class_counts").AsObject();
      CountMap m;
      for( Object::iterator it = output_classes.begin(); it != output_classes.end(); ++it )
        m[(*it).first] = boost::lexical_cast<size_t>( (*it).second.ToString() );

      out_class_counts.clear();
      for( auto& a: m )
        out_class_counts.insert( CountMap::value_type(a.first,a.second) );
    }
  }

  bool hasShuffle() const
  {
    return shuffle;
  }

  bool hasSplit() const
  {
    return split;
  }

  NormalizationType getNormType() const
  {
    return norm;
  }

  const FieldInfos& getFieldInfos() const
  {
    return field_infos;
  }

  const std::string& getVersion() const
  {
    return version;
  }

  int getSplitStart() const
  {
    return split_start;
  }

  int getSplitEnd() const
  {
    return split_end;
  }

  BalancingType getBalancingType() const
  {
    return balancing;
  }

  CountVec getOutputClassCounts() const
  {
    CountVec a;
    a.push_back(0); // N/A
    for( auto& x: out_class_counts )
      a.push_back( x.second );
    return a;
  }
private:
  static IndexVec getColumns(Jzon::Object& o)
  {
    IndexVec a;
    const Jzon::Array &cols = o.Get("columns").AsArray();
    for (Jzon::Array::const_iterator it = cols.begin(); it != cols.end(); ++it)
      a.push_back(boost::lexical_cast < size_t > ((*it).ToString()));
    std::sort(a.begin(), a.end());
    return a;
  }

private:
  NormalizationType norm;
  BalancingType balancing;
  bool shuffle;
  FieldInfos field_infos;
  std::string version;
  bool split;
  int split_start;
  int split_end;
  CountMap out_class_counts;

  // merge: ?
};

} // namespace dm
} // namespace ersatz

#endif // ERSATZ_DM_LoadConfig_h
