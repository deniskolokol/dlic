# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'TrainEnsemble.net_type'
        db.alter_column(u'job_trainensemble', 'net_type', self.gf('django.db.models.fields.CharField')(default='DEEPNET', max_length=20))

    def backwards(self, orm):

        # Changing field 'TrainEnsemble.net_type'
        db.alter_column(u'job_trainensemble', 'net_type', self.gf('django.db.models.fields.CharField')(max_length=20, null=True))

    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'data_management.datafile': {
            'Meta': {'ordering': "['-last_touch']", 'object_name': 'DataFile'},
            'bucket': ('django.db.models.fields.CharField', [], {'default': "'ersatz1test'", 'max_length': '255', 'blank': 'True'}),
            'celery_task_id': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'file_format': ('django.db.models.fields.CharField', [], {'max_length': '20', 'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255', 'blank': 'True'}),
            'last_touch': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'meta': ('jsonfield.fields.JSONField', [], {}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'shared': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'state': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'s3files'", 'to': u"orm['web.ApiUser']"}),
            'version': ('django.db.models.fields.IntegerField', [], {'default': '3'})
        },
        u'data_management.dataset': {
            'Meta': {'object_name': 'DataSet'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'data': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'datasets'", 'to': u"orm['data_management.DataFile']"}),
            'filters': ('jsonfield.fields.JSONField', [], {'default': '[]', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'iscreated': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'key': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'last_column_is_output': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'norm_min_max': ('jsonfield.fields.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'quantiles': ('jsonfield.fields.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'shared': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'state': ('django.db.models.fields.CharField', [], {'default': "'READY'", 'max_length': '15'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'datasets'", 'to': u"orm['web.ApiUser']"}),
            'version': ('django.db.models.fields.IntegerField', [], {'default': '2'})
        },
        u'job.learnmodel': {
            'Meta': {'object_name': 'LearnModel'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'detailed_results_file': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'null': 'True'}),
            'ensemble': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'learn_models'", 'to': u"orm['job.TrainEnsemble']"}),
            'error': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model_name': ('django.db.models.fields.CharField', [], {'default': "'MRNN'", 'max_length': '255'}),
            'model_params': ('jsonfield.fields.JSONField', [], {'default': '{}'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'readonly': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'sp_results': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'state': ('django.db.models.fields.CharField', [], {'default': "'NEW'", 'max_length': '10'}),
            'traceback': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'training_time': ('django.db.models.fields.FloatField', [], {'default': '0.0'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        u'job.learnmodelstat': {
            'Meta': {'object_name': 'LearnModelStat'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'data': ('jsonfield.fields.JSONField', [], {}),
            'discarded': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'iteration': ('django.db.models.fields.IntegerField', [], {}),
            'model': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'stats'", 'to': u"orm['job.LearnModel']"}),
            'readonly': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            's3_data': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'test_accuracy': ('django.db.models.fields.FloatField', [], {}),
            'train_accuracy': ('django.db.models.fields.FloatField', [], {})
        },
        u'job.predict': {
            'Meta': {'object_name': 'Predict'},
            'ensemble': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'predicts'", 'to': u"orm['job.PredictEnsemble']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'iteration': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'predicts'", 'to': u"orm['job.LearnModelStat']"})
        },
        u'job.predictensemble': {
            'Meta': {'object_name': 'PredictEnsemble'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'dataset': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['data_management.DataSet']", 'null': 'True', 'blank': 'True'}),
            'error': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'input_data': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'iterations': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['job.LearnModelStat']", 'through': u"orm['job.Predict']", 'symmetrical': 'False'}),
            'predicting_time': ('django.db.models.fields.FloatField', [], {'default': '0.0'}),
            'queue_key': ('django.db.models.fields.CharField', [], {'max_length': '40', 'null': 'True'}),
            'results': ('jsonfield.fields.JSONField', [], {'null': 'True'}),
            's3key': ('django.db.models.fields.CharField', [], {'max_length': '250', 'null': 'True', 'blank': 'True'}),
            'state': ('django.db.models.fields.CharField', [], {'default': "'NEW'", 'max_length': '10'}),
            'traceback': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'predict_ensembles'", 'to': u"orm['web.ApiUser']"})
        },
        u'job.trainensemble': {
            'Meta': {'ordering': "['-id']", 'object_name': 'TrainEnsemble'},
            'canceled': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'config': ('jsonfield.fields.JSONField', [], {'null': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'data_type': ('django.db.models.fields.CharField', [], {'max_length': '20', 'null': 'True'}),
            'deleted': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'error': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'net_type': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'old_data': ('jsonfield.fields.JSONField', [], {'null': 'True'}),
            'options': ('jsonfield.fields.JSONField', [], {'default': '{}'}),
            'out_nonlin': ('django.db.models.fields.CharField', [], {'default': "'SOFTMAX'", 'max_length': '20', 'null': 'True'}),
            'quantiles': ('jsonfield.fields.JSONField', [], {'null': 'True'}),
            'queue_key': ('django.db.models.fields.CharField', [], {'max_length': '40', 'null': 'True'}),
            'send_email_on_change': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'send_queue_time': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'shared': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'state': ('django.db.models.fields.CharField', [], {'default': "'EMPTY'", 'max_length': '15'}),
            'test_dataset': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'ensembles_as_test'", 'null': 'True', 'to': u"orm['data_management.DataSet']"}),
            'traceback': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'train_dataset': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'ensembles_as_train'", 'null': 'True', 'to': u"orm['data_management.DataSet']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'train_ensembles'", 'to': u"orm['web.ApiUser']"}),
            'valid_dataset': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'ensembles_as_valid'", 'null': 'True', 'to': u"orm['data_management.DataSet']"})
        },
        u'web.apiuser': {
            'Meta': {'object_name': 'ApiUser'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'unique': 'True', 'max_length': '100', 'db_index': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_admin': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'login_count': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'seconds_paid': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'seconds_spent': ('django.db.models.fields.FloatField', [], {'default': '0.0'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        }
    }

    complete_apps = ['job']