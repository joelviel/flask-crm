#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime, sys
sys.path.insert(0, 'lib.zip')
from google.appengine.api import users, app_identity, mail
from google.appengine.ext import ndb
from flask import Flask, render_template, jsonify, request, redirect, make_response

app = Flask(__name__)

app.jinja_env.line_statement_prefix = '#'
app.jinja_env.line_comment_prefix = '##'

### Constants

COLORS = [
                '#c74b16',
                '#6c16c7',
                '#8d9fd2',
                '#c71f16',
                '#16a9c7',
                '#c7c116',
                '#1663c7',
                '#16c72e',
                '#986e4c',
                '#c7166f',
                '#86c716',
                '#16c79e',
                '#2516c7',
                '#107b89',
                '#c76f16',
                '#bb2581',
                '#475c7a',
                '#b20c1d',
                '#be9f9a',
                '#1a6b47'
            ]

### Models

class Root(ndb.Model): pass
ROOT =  Root.get_or_insert(app_identity.get_application_id())

class Customer(ndb.Model):
    name        = ndb.StringProperty()
    tags        = ndb.StringProperty(repeated=True)
    channels    = ndb.StringProperty(repeated=True)
    timer       = ndb.IntegerProperty(default=0)
    address     = ndb.JsonProperty(default=dict(city=None, state=None, street=None, zip=None))
    income      = ndb.IntegerProperty(default=0)
    created     = ndb.DateTimeProperty(auto_now_add=True)
    modified    = ndb.DateTimeProperty(auto_now=True)
    owner       = ndb.UserProperty(default=None)
    phone       = ndb.StringProperty()


    @classmethod
    def all(cls, search=None, sort=None):
        
        results         = []
        all_customers   = cls.query(ancestor=ROOT.key).filter(cls.owner == users.get_current_user()).fetch()

        if search:
            for customer in all_customers:
                if customer.name.lower().startswith(search.lower()) or search in customer.channels + customer.tags:
                    results.append(customer)

        else: results = all_customers


        if sort and results:
            results.sort(key=lambda x: getattr(x,sort.split(' ')[0]), reverse='DESC' in sort)

        return results

    @classmethod
    def all_owners(cls):
        all_customers = cls.query(ancestor=ROOT.key).fetch()
        
        all_owners = {}
        for customer in all_customers:
            all_owners[customer.owner.email()] = all_owners.get(customer.owner.email(), 0) + 1
        return all_owners

class AppUser(ndb.Model):
    google_account = ndb.UserProperty(default=None)
    max_customers  = ndb.IntegerProperty(default=20)
    created        = ndb.DateTimeProperty(auto_now_add=True)
    usage          = ndb.DateTimeProperty(repeated=True)
    tags           = ndb.PickleProperty(default={})


    @classmethod    
    def get_current(cls):
        return cls.query(ancestor=ROOT.key).filter(cls.google_account==users.get_current_user()).get()

    @classmethod    
    def is_known(cls):
        return bool(cls.get_current())

    @classmethod
    def all(cls):
        return cls.query(ancestor=ROOT.key).fetch()

    @property
    def has_quota(self):
        owners = Customer.all_owners()
        user_email = users.get_current_user().email()
        return True if user_email not in owners else owners[user_email] < self.max_customers


    def get_next_tag_color(self):
        
        color_indexes = []

        for element in self.tags.values():
            color_indexes.append(element['color_index'])

        color_occurences = [color_indexes.count(x) for x in range(len(COLORS))]
        
        return color_occurences.index(min(color_occurences))

    def update_usage(self):
        now = datetime.datetime.now()
        if self.usage[-1].date() != now.date():
            self.usage.append(now)
            self.put()

    def update_tags(self, tags_to_be_added, tags_to_be_deleted):
        
        unique_tags_to_be_added = []
        unique_tags_to_be_deleted = []

        if not tags_to_be_added and not tags_to_be_deleted:
            do_put = False

        else:
            do_put = True
        
            for tag in tags_to_be_added:
                try:
                    self.tags[tag]['occurence'] += 1
                except KeyError:
                    new_tag_color_index = self.get_next_tag_color()
                    self.tags[tag] = {'color_index': new_tag_color_index, 'occurence':1}
                    unique_tags_to_be_added.append({'tagName':tag, 'tagColorIdx':new_tag_color_index})

            for tag in tags_to_be_deleted:
                self.tags[tag]['occurence'] -= 1
                if self.tags[tag]['occurence'] == 0:
                    del self.tags[tag]
                    unique_tags_to_be_deleted.append(tag)

        return self, do_put, unique_tags_to_be_added, unique_tags_to_be_deleted

    def get_tag_infos_for_jtable(self):
    
        jtableTagColors         = COLORS
        jtableTagNames          = []
        jtableTagColorIndexes   = []
        jtableTagOccurences     = []

        for key, value in self.tags.iteritems():
            jtableTagNames.append(key)
            jtableTagColorIndexes.append(value['color_index'])
            jtableTagOccurences.append(value['occurence'])

        return jtableTagColors, jtableTagNames, jtableTagColorIndexes, jtableTagOccurences


### Utils

def encode_keys(entities):
    return [dict(e.to_dict(exclude=['owner', 'created', 'modified']), **dict(key=e.key.urlsafe())) for e in entities]

def encode_key(entity):
    return encode_keys([entity])[0]

def decode_safekey(safekey):
    return ndb.Key(urlsafe=safekey)

def form_to_customer(form, customer):

    tags_to_be_added = []
    tags_to_be_deleted = []

    for key, value in form.iteritems():


        if key == 'key':
            continue
        
        if key == 'timer': 
            try: value = int(value)
            except ValueError: value=0
        
        if key == 'channels':
            value = value.strip().replace(" ", "").split(',')
        
        if key == 'tags':
            value = value.strip().replace(" ", "").split(',')
            
            new_tags = value
            old_tags = customer.tags

            tags_to_be_deleted = [ tag for tag in old_tags if tag not in new_tags]
            tags_to_be_added   = [ tag for tag in new_tags if tag not in old_tags]


        setattr(customer, key, value)
    
    return customer, tags_to_be_added, tags_to_be_deleted

def get_google_user_info():
    return users.get_current_user(), users.is_current_user_admin(), users.create_login_url('/'), users.create_logout_url('/')


### Routes

@app.route('/')
def index():
    
    if not users.get_current_user():
        return redirect('/login')

    user, user_is_admin, login_url, logout_url = get_google_user_info()
    app_user = AppUser.get_current()
    
    if not app_user:
        AppUser(parent=ROOT.key, google_account=users.get_current_user(), usage=[datetime.datetime.now()]).put()
        app_user = AppUser.get_current()
    app_user.update_usage()
    
    navbar_customers = 'active'

    return render_template('index.html', **locals())


@app.route('/login')
def login():
    user, user_is_admin, login_url, logout_url = get_google_user_info()
    if user:
        return redirect('/')
    return render_template('login.html',  **locals())


@app.route('/recommend', methods=['POST'])
def recommend():
    sender          = users.get_current_user()
    recipient_email = request.form['email']

    if not mail.is_email_valid(recipient_email):
        response = jsonify(message='Invalid email')
        response.status_code = 406
        return response

    else:

        message = mail.EmailMessage(
            sender=sender.email(),
            subject="I recommend u this app")

        message.to = recipient_email
        message.body = """Check out http://flask-crm.appspot.com"""
        message.send()
        return jsonify()

@app.route('/admin')
def admin():
    user, user_is_admin, login_url, logout_url = get_google_user_info()
    navbar_admin = 'active'
    
    owners      = Customer.all_owners()
    app_users   = AppUser.all()
    app_user    = AppUser.get_current()
    
    return render_template('admin.html', **locals())


@app.route('/api/read/customers', methods=['GET'])
def get_customers():
    app_user = AppUser.get_current()
    customers = Customer.all(request.args.get('search'), request.args.get('jtSorting'))
    jtable_tag_infos = app_user.get_tag_infos_for_jtable()
    return jsonify(Result='OK', Records=encode_keys(customers), jtableTagColors=jtable_tag_infos[0], jtableTagNames= jtable_tag_infos[1], jtableTagColorIndexes=jtable_tag_infos[2], jtableTagOccurences=jtable_tag_infos[3])

@app.route('/api/create/customers', methods=['POST'])
def create_customer():
    
    app_user = AppUser.get_current()

    if app_user.has_quota:
        
        new_customer, tags_to_be_added,  tags_to_be_deleted = form_to_customer(request.form, Customer(parent=ROOT.key, owner=users.get_current_user()))
        app_user, put_user, unique_tags_to_be_added, unique_tags_to_be_deleted = app_user.update_tags(tags_to_be_added, tags_to_be_deleted)

        if put_user:
            ndb.put_multi([new_customer, app_user])
        else:
            new_customer.put()

        jtable_tag_infos = app_user.get_tag_infos_for_jtable()
        return jsonify(Result='OK', Record=encode_key(new_customer), jtableAddTags= unique_tags_to_be_added, jtableDeleteTags=unique_tags_to_be_deleted)

    else:
        return jsonify(Result='ERROR', Message='You cannot create more than '+str(app_user.max_customers) +' customers')


@app.route('/api/update/customers', methods=['POST'])
def update_customer():
    app_user = AppUser.get_current()
    updated_customer, tags_to_be_added, tags_to_be_deleted = form_to_customer(request.form, decode_safekey(request.form['key']).get())
    app_user, put_user, unique_tags_to_be_added, unique_tags_to_be_deleted = app_user.update_tags(tags_to_be_added,  tags_to_be_deleted)
    
    if put_user:
        ndb.put_multi([updated_customer, app_user])
    else:
        updated_customer.put()
    
    return jsonify(Result='OK',  jtableAddTags=unique_tags_to_be_added, jtableDeleteTags=unique_tags_to_be_deleted)


@app.route('/api/delete/customers', methods=['POST'])
def delete_customer():
    app_user = AppUser.get_current()
    delete_customer = decode_safekey(request.form['key']).get()
    app_user, put_user, unique_tags_to_be_added, unique_tags_to_be_deleted = app_user.update_tags(tags_to_be_added=[],  tags_to_be_deleted=delete_customer.tags)
    if put_user: app_user.put()
    delete_customer.key.delete()
    return jsonify(Result='OK', jtableAddTags=[], jtableDeleteTags=unique_tags_to_be_deleted)