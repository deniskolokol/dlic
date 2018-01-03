import mock

def upload_modeldata_mock():
    def local_upload_modeldata(data, load_file, model_id):
        return 's3_data_path'
    return mock.patch('ersatz.aws.upload_modeldata', local_upload_modeldata)
