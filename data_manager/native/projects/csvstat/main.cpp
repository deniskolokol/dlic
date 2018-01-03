#include <iostream>
#include <ersatz/dm/CSVStat.h>
#include <ersatz/dm/TableLoader.h>

void printUsage()
{
  std::cout << "Ersatz CSV analyzer." << std::endl;
  std::cout << std::endl;
  std::cout << "1. parsing" << std::endl;
  std::cout << "   csvstat parse <csv file>" << std::endl;
  std::cout << "     Read csv file and produce column statistics as described in " << std::endl;
  std::cout << "     https://github.com/davebs/MRNN/wiki/Data-manager-metadata-format#csv-specific-data_type--general" << std::endl;
  std::cout << std::endl;
  std::cout << "2. loading" << std::endl;
  std::cout << "   csvstat load <csv file> <hdf5 file> <load config file>" << std::endl;
  std::cout << "     Transform csv data to hdf5 format for training (and prediction)." << std::endl;
  std::cout << "     Load config file describes what transformation should be applied for the dataset such as changing columnt types, normalization, sampling." << std::endl;
  std::cout << "     Syntax of the config file is JSON. For possible configuration options see the following example:" << std::endl;
}

void parse( const char * csv_file_name )
{
  using namespace ersatz::utils;
  using namespace ersatz::dm;

  CSVStat stat;
  stat.analize(csv_file_name);
  stat.toJSON();
}

void load( const char * csv_file_name, const char * hdf5_file_name, const char * tranformation_config )
{
  using namespace ersatz::utils;
  using namespace ersatz::dm;

  loadTable( csv_file_name, hdf5_file_name, tranformation_config );
}

int main(int argc, char **argv)
{
  using namespace ersatz::utils;
  using namespace ersatz::dm;

  using namespace Jzon;

  try
  {
    if( argc == 3 && strcmp("parse", argv[1])==0 )
    {
      parse( argv[2] );
    }
    else if( (argc == 4 || argc==5) && strcmp("load", argv[1])==0 )
    {
      load( argv[2], argv[3], (argc==5 ? argv[4] : 0) );
    }
    else
    {
      printUsage();
      return 1;
    }
    return 0;
  }
  catch (const UserException& e)
  {
    logUserError(e.what());
    return 1;
  }
  catch (const Exception& e)
  {
    logFatalError(e.what(), e.debugInfo());
    return 2;
  }
  catch (...)
  {
    logUserError("First row is empty, it must contain headers or data.\nThis means your file isn't properly formatted\n(or you submitted another type of file).");
    return 3;
  }
  /*catch (const Exception& e)
  {
    logFatalError(e.what(), e.debugInfo());
    return 2;
  }
  catch (const std::exception& e)
  {
    logFatalError(e.what());
    return 3;
  }
  catch (...)
  {
    logFatalError("Unknown");
    return 4;
  }*/
}
