import logging
import math
from itertools import chain
from django.db import models
from django.db.models import F, get_model, Count, Max, Q
from django.contrib.auth.models import (BaseUserManager, AbstractBaseUser,
                                        PermissionsMixin)
from django.contrib.auth.signals import user_logged_in


logger = logging.getLogger(__name__)


class ApiUserManager(BaseUserManager):
    def create_user(self, email, password=None):
        """
        Creates and saves a User with the given email, date of
        birth and password.
        """
        if not email:
            raise ValueError('Users must have an email address')

        user = self.model(
            email=ApiUserManager.normalize_email(email),
        )

        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password):
        """
        Creates and saves a superuser with the given email, date of
        birth and password.
        """
        user = self.create_user(email, password=password)
        user.is_admin = True
        user.is_superuser = True
        user.save(using=self._db)
        return user


class ApiUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(
        verbose_name='email address',
        max_length=100,
        unique=True,
        db_index=True,
    )
    is_active = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False)
    login_count = models.IntegerField('number of user\'s logins', default=0)
    date_joined = models.DateTimeField(auto_now_add=True,
                                       verbose_name='date joined')
    seconds_paid = models.IntegerField(default=0)
    seconds_spent = models.FloatField(default=0.0)

    objects = ApiUserManager()

    USERNAME_FIELD = 'email'

    def get_full_name(self):
        return self.email

    def get_short_name(self):
        return self.email

    def __unicode__(self):
        return self.email

    @property
    def is_staff(self):
        return self.is_admin

    @property
    def minutes_spent(self):
        return int(math.ceil(self.seconds_spent / 60.))

    @property
    def minutes_paid(self):
        return self.seconds_paid / 60

    @property
    def minutes_delta(self):
        return int(self.seconds_paid / 60 - self.seconds_spent / 60)

    @property
    def is_paid(self):
        return self.seconds_paid > self.seconds_spent

    def not_deleted_s3files(self):
        return self.s3files.not_deleted()

    def shared_s3files(self):
        DataFile = get_model('data_management', 'DataFile')
        return DataFile.objects.exclude(user=self).filter(shared=True)

    def s3files_with_shared(self):
        return list(chain(self.s3files.not_deleted(), self.shared_s3files()))

    def supported_training_s3files(self):
        DataSet = get_model('data_management', 'DataSet')
        return DataSet.objects.filter(Q(user=self) | Q(shared=True))

    def supported_training_s3files_ts(self):
        qs = self.supported_training_s3files()
        return qs.filter(data__file_format='TIMESERIES')

    def supported_training_s3files_general(self):
        qs = self.supported_training_s3files()
        return qs.filter(data__file_format='GENERAL')

    def render_intercom_data(self):
        LearnModel = get_model('job', 'LearnModel')
        LearnModelStat = get_model('job', 'LearnModelStat')
        custom_data = {s[0].lower() + '_models': 0
                       for s in LearnModel.TRAIN_STATES}
        custom_data['credit_used'] = self.minutes_spent
        finished_scores = LearnModelStat.objects \
            .filter(model__state='FINISHED', model__ensemble__user=self) \
            .values_list('model') \
            .annotate(best_test=Max('test_accuracy'),
                      best_train=Max('train_accuracy'))
        if finished_scores:
            train_acc, test_acc = zip(*finished_scores)[1:]
            custom_data['avg_train_acc'] = \
                round(sum(train_acc) / len(train_acc), 3)
            custom_data['avg_test_acc'] = \
                round(sum(test_acc) / len(test_acc), 3)
        else:
            custom_data['avg_train_acc'] = 'null'
            custom_data['avg_test_acc'] = 'null'
        states = LearnModel.objects.filter(ensemble__user=self) \
            .values_list('state').annotate(count=Count('state'))
        states = {s[0].lower() + '_models': s[1] for s in states}
        custom_data.update(states)
        custom_data['files'] = self.not_deleted_s3files().count()
        return ','.join([k + ': ' + str(v) for k, v in custom_data.items()])


#signals
def count_user_login(sender, user, **kwargs):
    user.login_count = F('login_count') + 1
    user.save()


user_logged_in.connect(count_user_login)
