#ifndef ERSATZ_DM_TableLoader_h
#define ERSATZ_DM_TableLoader_h

#include <map>
#include <Jzon.h>
#include <ersatz/utils/io.h>
#include <ersatz/dm/LoadConfig.h>
#include <ersatz/dm/TableEncoder.h>
#include <ersatz/dm/HDF5DataSetWriter.h>

namespace ersatz
{
namespace dm
{

void loadTable( const char * csv_file_name, const char * hdf5_file_name, const char * load_cfg_file_name )
{
  using namespace ersatz::utils;
  using namespace ersatz::dm;

  LoadConfig cfg;
  if( load_cfg_file_name )
    cfg.load( load_cfg_file_name );

  // build filter chain
  SPRecordSourceVec filters;
  TableEncoder * t = new TableEncoder(csv_file_name, cfg);
  size_t n = t->getWidth();
  size_t last_width = t->getOuputWidth();
  filters.push_back( SPRecordSource(t) );

  // balancing
  E_ASSERT( cfg.getBalancingType() == BT_None || last_width == 1  );
  if( cfg.getBalancingType() == BT_Undersample )
    filters.push_back( SPRecordSource( new UnderSampler(*filters.back(), n-1, cfg.getOutputClassCounts() )) );
  else if( cfg.getBalancingType() == BT_Oversample )
    filters.push_back( SPRecordSource( new OverSampler(*filters.back(), n-1, cfg.getOutputClassCounts() )) );
  //else if( cfg.getBalancingType() == BT_Uniform )
    //filters.push_back( SPRecordSource( new UniformSampler(*filters.back(), n-1, cfg.getOutputClassCounts() )) );

  // shuffle
  if( cfg.hasShuffle() )
    filters.push_back( SPRecordSource(new SimpleShuffle(*filters.back())) );

  // split
  if( cfg.hasSplit() )
    filters.push_back( SPRecordSource(new Split(*filters.back(), cfg.getSplitStart(), cfg.getSplitEnd() )) );

  // run filter chain
  SPRecordSource src = filters.back();
  report("Encoding data...");
  HDF5DataSetWriter w( hdf5_file_name, n-last_width, last_width, cfg.getVersion() );
  FMtx mtx;
  while( src->getNext(1000,mtx) )
  {
    for( auto& rec: mtx )
      w.append( rec.begin(), rec.begin() + n - last_width, rec.begin() + n - last_width, rec.end());
  }
}


} // namespace dm
} // namespace ersatz

#endif // ERSATZ_DM_TableLoader_h
