import json
import pytest
from django.core.urlresolvers import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from data_management.models import DataFile, DataSet
from job.models import TrainEnsemble, LearnModel


# we don't use py.test style (TestCase) because django provides assertion
# for number of queries performed during code execution


@pytest.mark.usefixtures('class_setup')
class TestData(APITestCase):
    def test_data_list(self):
        DataFile.objects.create(user=self.user,
                                key='uploads/111aaa/test.ts',
                                file_format='TIMESERIES')
        DataFile.objects.create(user=self.user,
                                key='uploads/222aaa/data.zip',
                                file_format='IMAGES',
                                meta={'classes': [0, 1, 2],
                                      'key': 'uploads/222aaa/data.zip'})
        DataFile.objects.create(user=self.user,
                                key='uploads/333aaa/test3.csv.gz',
                                file_format='GENERAL')
        url = reverse('data-list') + '?key=' + self.user.apikey.key
        with self.assertNumQueries(4):
            response = self.client.get(url, format='json')
        assert response.status_code == status.HTTP_200_OK
        assert len(json.loads(response.content)) == 3


@pytest.mark.usefixtures('class_setup')
class TestEnsemble(APITestCase):
    def test_ensemble_list(self):
        s3file1 = DataFile.objects.create(user=self.user,
                                          key='uploads/111aaa/test.ts',
                                          file_format='TIMESERIES')
        key = 'uploads/222aaa/data.zip'
        s3file2 = DataFile.objects.create(user=self.user,
                                          key=key,
                                          file_format='IMAGES',
                                          meta={'classes': [0, 1, 2],
                                                'key': key})
        s3file3 = DataFile.objects.create(user=self.user,
                                          key='uploads/333aaa/test3.csv.gz',
                                          file_format='GENERAL')
        dataset1 = DataSet.objects.create(
            name='Ds 1', key='dataset/' + s3file1.key,
            data=s3file1, user=s3file1.user
        )
        dataset2 = DataSet.objects.create(
            name='Ds 2', key='dataset/' + s3file2.key,
            data=s3file2, user=s3file2.user
        )
        dataset3 = DataSet.objects.create(
            name='Ds 3', key='dataset/' + s3file3.key,
            data=s3file3, user=s3file3.user
        )
        ensemble1 = TrainEnsemble.objects.create(
            user=dataset1.user,
            train_dataset=dataset1,
            test_dataset=dataset2,
            data_type=TrainEnsemble.TIMESERIES
        )
        for _ in range(10):
            LearnModel.objects.create(
                ensemble=ensemble1,
                model_name='MRNN'
            )

        ensemble2 = TrainEnsemble.objects.create(
            user=dataset1.user,
            train_dataset=dataset2,
            test_dataset=dataset3,
            data_type=TrainEnsemble.TIMESERIES
        )
        for _ in range(1):
            LearnModel.objects.create(
                ensemble=ensemble2,
                model_name='MRNN'
            )

        ensemble3 = TrainEnsemble.objects.create(
            user=dataset1.user,
            train_dataset=dataset3,
            test_dataset=dataset1,
            data_type=TrainEnsemble.TIMESERIES
        )
        for _ in range(2):
            LearnModel.objects.create(
                ensemble=ensemble3,
                model_name='MRNN'
            )

        ensemble4 = TrainEnsemble.objects.create(
            user=dataset1.user,
            train_dataset=dataset3,
            test_dataset=dataset2,
            data_type=TrainEnsemble.TIMESERIES
        )
        for _ in range(2):
            LearnModel.objects.create(
                ensemble=ensemble4,
                model_name='MRNN'
            )
        url = reverse('ensemble-list') + '?key=' + self.user.apikey.key
        with self.assertNumQueries(2):
            response = self.client.get(url, format='json')
        assert response.status_code == status.HTTP_200_OK
        assert len(json.loads(response.content)) == 4
