#ifndef ERSATZ_DM_HDF5DataSetWriter_h
#define ERSATZ_DM_HDF5DataSetWriter_h

#include <vector>
#include <boost/noncopyable.hpp>
#include <hdf5.h>
#include <ersatz/dm/Common.h>

namespace ersatz
{
namespace dm
{

class HDF5Float32MatrixWriter: private boost::noncopyable
{
public:
  HDF5Float32MatrixWriter(hid_t h5_file, const char * data_set_name, size_t _cols, size_t _chunk_size = 10000)
      : cols(_cols), chunk_size(_chunk_size), rows_in_current_chunk(0)
  {
    hid_t prop = H5Pcreate(H5P_DATASET_CREATE);
    hsize_t counts[] = { chunk_size, cols };
    H5Pset_chunk( prop, 2, counts );
    dims = { 0,cols};
    hsize_t max_dims[] = { H5S_UNLIMITED, cols };
    hid_t ds = H5Screate_simple( 2, dims.data(), max_dims );
    dataset = H5Dcreate1( h5_file, data_set_name, H5T_IEEE_F32LE, ds, prop );
    H5Sclose(ds);
    H5Pclose(prop);
  }

  virtual ~HDF5Float32MatrixWriter()
  {
    flush();
    H5Dclose( dataset );
  }

  void append(const FVec::const_iterator begin, const FVec::const_iterator end)
  {
    buff.insert(buff.end(), begin, end);
    if (++rows_in_current_chunk == chunk_size)
      flush();
  }

  void flush()
  {
    if (buff.empty())
      return;

    hsize_t copy_pos = dims[0];

    // extend number of rows
    dims[0] += rows_in_current_chunk;
    H5Dextend( dataset, dims.data() );

    // copy chunk
    hid_t filespace = H5Dget_space(dataset);
    Sizes counts = { rows_in_current_chunk, cols };
    Sizes starts = { copy_pos, 0 };
    H5Sselect_hyperslab( filespace, H5S_SELECT_SET, starts.data(), 0, counts.data(), 0 );
    hid_t memspace = H5Screate_simple( 2, counts.data(), counts.data() );
    H5Dwrite( dataset, H5T_IEEE_F64LE, memspace, filespace, H5P_DEFAULT, (void*)buff.data() );

    // clear buf
    buff.clear();
    rows_in_current_chunk = 0;
  }

  void addStrAttrib(const std::string& name, const std::string& val)
  {
    hid_t str_type = H5Tcopy(H5T_C_S1);
    H5Tset_size(str_type, val.size());
    hid_t att_space = H5Screate(H5S_SCALAR);
    hid_t att = H5Acreate1( dataset, name.c_str(), str_type, att_space, H5P_DEFAULT);
    H5Awrite( att, str_type, val.c_str());
    H5Tclose( str_type );
    H5Aclose( att );
  }
private:
  typedef std::vector<hsize_t> Sizes;
private:
  FVec buff;
  size_t cols;
  size_t chunk_size;
  size_t rows_in_current_chunk;
  Sizes dims;
  hid_t dataset;
};

/**
 * Streaming writer for binary hdf5 files compatible with Pylearn's HDF5Dataset.
 * http://deeplearning.net/software/pylearn2/library/datasets.html#pylearn2.datasets.hdf5.HDF5Dataset
 */
class HDF5DataSetWriter: private boost::noncopyable
{
public:
  typedef hsize_t Size;
  typedef std::vector<Size> Sizes;
public:
  HDF5DataSetWriter(const char * file_name, Size input_cols, Size output_cols, const std::string& attrib_version, Size row_chunk_size = 10000)
  {
    h5_file = H5Fcreate( file_name, H5F_ACC_TRUNC, H5P_DEFAULT, H5P_DEFAULT );
    E_ASSERT( h5_file >=0 );
    E_ASSERT( input_cols > 0 );

    data_writer.reset( new HDF5Float32MatrixWriter(h5_file, "data", input_cols, row_chunk_size ) );
    if( output_cols > 0)
      output_writer.reset( new HDF5Float32MatrixWriter(h5_file, "output", output_cols, row_chunk_size) );

    data_writer->addStrAttrib("source_data_type", "GENERAL");
    data_writer->addStrAttrib("version", attrib_version);
  }

  virtual ~HDF5DataSetWriter()
  {
    H5Fclose(h5_file);
  }

  void append(const FVec::const_iterator in_begin, const FVec::const_iterator in_end, const FVec::const_iterator out_begin, const FVec::const_iterator out_end)
  {
    data_writer->append(in_begin, in_end);
    if( output_writer )
      output_writer->append(out_begin, out_end);
  }

  void flush()
  {
    data_writer->flush();
    if( output_writer )
      output_writer->flush();
  }

private:
  hid_t h5_file;
  std::shared_ptr<HDF5Float32MatrixWriter> data_writer;
  std::shared_ptr<HDF5Float32MatrixWriter> output_writer;
};

} // namespace dm
} // namespace ersatz

#endif // ERSATZ_DM_HDF5DataSetWriter_h
