# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'TrainEnsemble'
        db.create_table(u'job_trainensemble', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(related_name='train_ensembles', to=orm['web.ApiUser'])),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('file_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['web.UserFile'], null=True, blank=True)),
            ('file_url', self.gf('django.db.models.fields.URLField')(max_length=200, null=True)),
            ('queue_key', self.gf('django.db.models.fields.CharField')(max_length=40, null=True)),
        ))
        db.send_create_signal(u'job', ['TrainEnsemble'])

        # Adding model 'LearnModel'
        db.create_table(u'job_learnmodel', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('ensemble', self.gf('django.db.models.fields.related.ForeignKey')(related_name='learn_models', to=orm['job.TrainEnsemble'])),
            ('model_name', self.gf('django.db.models.fields.CharField')(default='MRNN', max_length=255)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('updated', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('state', self.gf('django.db.models.fields.CharField')(default='NEW', max_length=10)),
            ('error', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
        ))
        db.send_create_signal(u'job', ['LearnModel'])

        # Adding model 'TrainEnsembleStat'
        db.create_table(u'job_trainensemblestat', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('ensemble', self.gf('django.db.models.fields.related.ForeignKey')(related_name='stats', to=orm['job.TrainEnsemble'])),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('data', self.gf('jsonfield.fields.JSONField')()),
        ))
        db.send_create_signal(u'job', ['TrainEnsembleStat'])

        # Adding model 'LearnModelStat'
        db.create_table(u'job_learnmodelstat', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('model', self.gf('django.db.models.fields.related.ForeignKey')(related_name='stats', to=orm['job.LearnModel'])),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('data', self.gf('jsonfield.fields.JSONField')()),
        ))
        db.send_create_signal(u'job', ['LearnModelStat'])


    def backwards(self, orm):
        # Deleting model 'TrainEnsemble'
        db.delete_table(u'job_trainensemble')

        # Deleting model 'LearnModel'
        db.delete_table(u'job_learnmodel')

        # Deleting model 'TrainEnsembleStat'
        db.delete_table(u'job_trainensemblestat')

        # Deleting model 'LearnModelStat'
        db.delete_table(u'job_learnmodelstat')


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
            'ensemble': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'learn_models'", 'to': u"orm['job.TrainEnsemble']"}),
            'error': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model_name': ('django.db.models.fields.CharField', [], {'default': "'MRNN'", 'max_length': '255'}),
            'state': ('django.db.models.fields.CharField', [], {'default': "'NEW'", 'max_length': '10'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        u'job.learnmodelstat': {
            'Meta': {'object_name': 'LearnModelStat'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'data': ('jsonfield.fields.JSONField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'stats'", 'to': u"orm['job.LearnModel']"})
        },
        u'job.trainensemble': {
            'Meta': {'object_name': 'TrainEnsemble'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'file_id': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['web.UserFile']", 'null': 'True', 'blank': 'True'}),
            'file_url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'queue_key': ('django.db.models.fields.CharField', [], {'max_length': '40', 'null': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'train_ensembles'", 'to': u"orm['web.ApiUser']"})
        },
        u'job.trainensemblestat': {
            'Meta': {'object_name': 'TrainEnsembleStat'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'data': ('jsonfield.fields.JSONField', [], {}),
            'ensemble': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'stats'", 'to': u"orm['job.TrainEnsemble']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        u'web.apiuser': {
            'Meta': {'object_name': 'ApiUser'},
            'email': ('django.db.models.fields.EmailField', [], {'unique': 'True', 'max_length': '100', 'db_index': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_admin': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'web.userfile': {
            'Meta': {'object_name': 'UserFile'},
            'bucket': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'etag': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            's3file': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'s3files'", 'to': u"orm['web.ApiUser']"})
        }
    }

    complete_apps = ['job']