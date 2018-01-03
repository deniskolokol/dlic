#ifndef ERSATZ_DM_TableEncoder_h
#define ERSATZ_DM_TableEncoder_h

#include <ersatz/dm/Common.h>
#include <ersatz/dm/ColumnEncoder.h>
#include <ersatz/dm/Filter.h>
#include <ersatz/dm/LoadConfig.h>
#include <ersatz/utils/io.h>

namespace ersatz
{
namespace dm
{

class TableEncoder : public RecordSource
{
public:
  TableEncoder( const char * file_name, const LoadConfig& _load_cfg )
    : file_reader(file_name), load_cfg(_load_cfg)
  {
    using namespace ersatz::utils;

    // count lines in file
    report("Scanning data...");
    FileReader fr( file_name );
    CSVParser cp;
    lines = 0;
    if( cp.readNextRecord(fr.getInput()) && !cp.isHeader() )
      lines++;
    StrRef line;
    while( readLineAllOS(fr.getInput(), line) )
      lines++;

    // create column encoders
    cols = load_cfg.getFieldInfos().size();
    width = 0;
    output_width = 0;
    column_encoders.resize( cols );
    for( size_t i=0; i<cols; ++i )
    {
      // create the encoder
      column_encoders[i].reset( createColumnEncoder(load_cfg.getFieldInfos()[i], load_cfg.getNormType()) );
      width += column_encoders[i]->getEncodedSize();

      // fill input and output column indexes
      if( load_cfg.getFieldInfos()[i].output )
      {
        output_columns.push_back(i);
        output_width += column_encoders[i]->getEncodedSize();
      }
      else
      {
        input_columns.push_back(i);
      }
    }
  }

  virtual size_t getSize()
  {
    return lines;
  }

  size_t getWidth() const
  {
    return width;
  }

  size_t getOuputWidth() const
  {
    return output_width;
  }

  virtual bool getNext( size_t n, FMtx& mtx )
  {
    mtx.resize(n,FVec(width));

    size_t i = 0;
    while( i<n )
    {
      // read next record
      if( !csv_parser.readNextRecord(file_reader.getInput()) )
      {
        mtx.resize(i);
        return i>0;
      }

      // invalid row or header
      if( csv_parser.getRecord().size() < cols || csv_parser.isHeader() )
        continue;

      // use column encoders to encode fields
      bool valid_row = true;
      FVec::iterator it = mtx[i].begin();

      // input columns
      for( size_t i: input_columns )
      {
        if( !column_encoders[i]->encode( csv_parser.getRecord()[i], it ) )
        {
          valid_row = false;
          break;
        }
      }

      // output columns
      for( size_t i: output_columns )
      {
        if( !column_encoders[i]->encode( csv_parser.getRecord()[i], it ) )
        {
          valid_row = false;
          break;
        }
      }

      if( valid_row )
        ++i;
    }
    return true;
  }

private:
  typedef std::vector<SPColumnEncoder> ColumnEncoders;
private:
  ersatz::utils::FileReader file_reader;
  ersatz::utils::CSVParser csv_parser;
  const LoadConfig& load_cfg;
  size_t cols;
  size_t width;
  size_t output_width;
  ColumnEncoders column_encoders;
  IndexVec input_columns;
  IndexVec output_columns;
  size_t lines;
};


} // namespace dm
} // namespace ersatz

#endif // ERSATZ_DM_TableEncoder_h
