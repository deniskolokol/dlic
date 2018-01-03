# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'TrainEnsemble.error'
        db.alter_column(u'job_trainensemble', 'error', self.gf('django.db.models.fields.TextField')(null=True))

        # Changing field 'LearnModel.error'
        db.alter_column(u'job_learnmodel', 'error', self.gf('django.db.models.fields.TextField')(null=True))

        # Changing field 'PredictEnsemble.error'
        db.alter_column(u'job_predictensemble', 'error', self.gf('django.db.models.fields.TextField')(null=True))

    def backwards(self, orm):

        # Changing field 'TrainEnsemble.error'
        db.alter_column(u'job_trainensemble', 'error', self.gf('django.db.models.fields.CharField')(max_length=255, null=True))

        # Changing field 'LearnModel.error'
        db.alter_column(u'job_learnmodel', 'error', self.gf('django.db.models.fields.CharField')(max_length=255, null=True))

        # Changing field 'PredictEnsemble.error'
        db.alter_column(u'job_predictensemble', 'error', self.gf('django.db.models.fields.CharField')(max_length=255, null=True))

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
        u'job.learnmodel': {
            'Meta': {'object_name': 'LearnModel'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'detailed_results_file': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'null': 'True'}),
            'ensemble': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'learn_models'", 'to': u"orm['job.TrainEnsemble']"}),
            'error': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model_name': ('django.db.models.fields.CharField', [], {'default': "'MRNN'", 'max_length': '255'}),
            'model_params': ('jsonfield.fields.JSONField', [], {'default': '{}'}),
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
            'error': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'file_id': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['web.UserFile']", 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'input_data': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'iterations': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['job.LearnModelStat']", 'through': u"orm['job.Predict']", 'symmetrical': 'False'}),
            'itershash': ('django.db.models.fields.CharField', [], {'max_length': '40', 'null': 'True'}),
            'predicting_time': ('django.db.models.fields.FloatField', [], {'default': '0.0'}),
            'queue_key': ('django.db.models.fields.CharField', [], {'max_length': '40', 'null': 'True'}),
            'results': ('jsonfield.fields.JSONField', [], {'null': 'True'}),
            'state': ('django.db.models.fields.CharField', [], {'default': "'NEW'", 'max_length': '10'}),
            'testset': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'traceback': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'predict_ensembles'", 'to': u"orm['web.ApiUser']"})
        },
        u'job.trainensemble': {
            'Meta': {'object_name': 'TrainEnsemble'},
            'auto_next_model': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'canceled': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'config': ('jsonfield.fields.JSONField', [], {'null': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'data_split': ('jsonfield.fields.JSONField', [], {'default': '[60, 20, 20]', 'null': 'True'}),
            'data_type': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'deleted': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'error': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'file_id': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['web.UserFile']", 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'out_nonlin': ('django.db.models.fields.CharField', [], {'default': "'SOFTMAX'", 'max_length': '20', 'null': 'True'}),
            'quantiles': ('jsonfield.fields.JSONField', [], {'null': 'True'}),
            'queue_key': ('django.db.models.fields.CharField', [], {'max_length': '40', 'null': 'True'}),
            'test_dataset': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'test_datasets'", 'null': 'True', 'to': u"orm['web.UserFile']"}),
            'traceback': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'train_ensembles'", 'to': u"orm['web.ApiUser']"}),
            'valid_dataset': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'valid_datasets'", 'null': 'True', 'to': u"orm['web.UserFile']"})
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
        },
        u'web.userfile': {
            'Meta': {'object_name': 'UserFile'},
            'bucket': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'deleted': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'etag': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            's3file': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'s3files'", 'to': u"orm['web.ApiUser']"})
        }
    }

    complete_apps = ['job']