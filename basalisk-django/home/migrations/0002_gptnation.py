from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Gptnation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('NATION', models.CharField(max_length=255)),
                ('X_PASSWORD', models.CharField(max_length=255)),
                ('USERAGENT', models.CharField(default='DarcOS', max_length=255)),
            ],
        ),
    ]
