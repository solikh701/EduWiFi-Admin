from app.extensions import db
import datetime


class User(db.Model):
    __tablename__ = 'user' 

    id = db.Column(db.Integer, primary_key=True)
    MAC = db.Column(db.String(40), index=True)
    last_tariff_limit = db.Column(db.String(30))
    fio = db.Column(db.String(50))
    phone_number = db.Column(db.String(20), nullable=False, index=True)
    confirmation_code = db.Column(db.String(10), nullable=True)
    overall_authorizations = db.Column(db.Integer)
    overall_payed_sum = db.Column(db.String(50))
    block = db.Column(db.Boolean)
    last_free_tariff_use = db.Column(db.String(50), nullable=True)
    free_tariff_limit = db.Column(db.Integer, default=0)
    comments = db.Column(db.String(100))
    latest_payed_amount = db.Column(db.String(20))
    latest_payed_transaction_id = db.Column(db.String(32), nullable=True)
    latest_payed_status = db.Column(db.String(20))
    merchant_trans_id = db.Column(db.Integer)
    role = db.Column(db.String(25))
    password       = db.Column(db.String(255))
    balance        = db.Column(db.String(50))
    payment_method = db.Column(db.String(50))
    link_login = db.Column(db.String(255), nullable=True)

    authorizations = db.relationship(
        'UserAuthorization',
        backref='user',
        lazy=True,
        primaryjoin="User.MAC == UserAuthorization.user_mac",
        foreign_keys='UserAuthorization.user_mac',
        cascade="all, delete-orphan"
    )

    def to_dict(self):
        last_authorization = max(self.authorizations, key=lambda auth: auth.authorization_date, default=None)
        return {
            'id': self.id,
            'MAC': self.MAC,
            'siteId': self.siteId,
            'fio': self.fio,
            'phone_number': self.phone_number,
            'last_authorization': last_authorization.authorization_date if last_authorization else None,
            'authorization_activeness': last_authorization.authorization_activeness if last_authorization else None,
            'confirmation_code': self.confirmation_code,
            'overall_authorizations': self.overall_authorizations,
            'overall_payed_sum': self.overall_payed_sum,
            'block': self.block,
            'free_tariff_limit': self.free_tariff_limit,
            'last_free_tariff_use': self.last_free_tariff_use,
            'comments': self.comments, 
            'balance': self.balance,
            'payment_method': self.payment_method,
            'link_login': self.link_login,
        }
    
    def get_valid_authorizations(self):
        return [
            {
                'authorization': (
                    auth.authorization_date.strftime("%Y-%m-%d %H:%M:%S")
                    if auth.authorization_date else None
                ),
                'selected_tariff': auth.selected_tariff,
                'tariff_limit': auth.tariff_limit,
                'authorization_activeness': auth.authorization_activeness
            }
            for auth in self.authorizations
        ]


class UserAuthorization(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_mac = db.Column(db.String(40), db.ForeignKey('user.MAC'), nullable=False)
    authorization_date = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    ip_address = db.Column(db.String(20))
    selected_tariff = db.Column(db.String(50))
    tariff_limit = db.Column(db.String(50))
    authorization_activeness = db.Column(db.String(20))
    link_login = db.Column(db.String(255), nullable=True)


class tariff_plan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    price = db.Column(db.String(50)) 
    is_active = db.Column(db.Boolean)
    duration_days = db.Column(db.String(50))
    rate_limit = db.Column(db.String(25))

    def to_dict(self):
        return {
            'id': self.id,
            'price': self.price,
            'is_active': self.is_active,
            'duration_days': self.duration_days, 
            'rate_limit': self.rate_limit, 
        }


class Settings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    switch1 = db.Column(db.Boolean)
    switch2 = db.Column(db.Boolean)
    switch3 = db.Column(db.Boolean)
    switch4 = db.Column(db.Boolean)
    switch5 = db.Column(db.Boolean)
    switch6 = db.Column(db.Boolean)
    file1Preview = db.Column(db.String(255), nullable=True)
    file2Preview = db.Column(db.String(255), nullable=True)
    freeTime = db.Column(db.String(50))  
    freeTimeRepeat = db.Column(db.String(50))
    docx = db.Column(db.Text, nullable=True)
    phone = db.Column(db.String(20)) 
    text1 = db.Column(db.String(255))
    text2 = db.Column(db.String(255))

    def to_dict(self):
        return {
            'id': self.id,
            'switch1': self.switch1,
            'switch2': self.switch2,
            'switch3': self.switch3,
            'switch4': self.switch4,
            'switch5': self.switch5,
            'switch6': self.switch6,
            'file1Preview': self.file1Preview,
            'file2Preview': self.file2Preview,
            'freeTime': self.freeTime,
            'freeTimeRepeat': self.freeTimeRepeat,
            'docx': self.docx,
            'phone': self.phone,
            'text1': self.text1,
            'text2': self.text2,
        }


class ReklamaData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    file1Preview = db.Column(db.String(255), nullable=True)
    file2Preview = db.Column(db.String(255), nullable=True)
    file3Preview = db.Column(db.String(255), nullable=True)
    file4Preview = db.Column(db.String(255), nullable=True)
    file5Preview = db.Column(db.String(255), nullable=True)
    duration1 = db.Column(db.Integer)
    duration2 = db.Column(db.Integer)
    duration3 = db.Column(db.Integer)
    duration4 = db.Column(db.Integer)
    duration5 = db.Column(db.Integer)
    date_start1 = db.Column(db.String(50))
    date_start2 = db.Column(db.String(50))
    date_start3 = db.Column(db.String(50))
    date_start4 = db.Column(db.String(50))
    date_start5 = db.Column(db.String(50))
    date_end1 = db.Column(db.String(50))  
    date_end2 = db.Column(db.String(50))  
    date_end3 = db.Column(db.String(50))  
    date_end4 = db.Column(db.String(50))  
    date_end5 = db.Column(db.String(50))  
    check1 = db.Column(db.Boolean)
    check2 = db.Column(db.Boolean)
    check3 = db.Column(db.Boolean)
    check4 = db.Column(db.Boolean)
    check5 = db.Column(db.Boolean)

    rek = db.Column(db.Boolean)
    reko = db.Column(db.Boolean)

    def to_dict(self):
        return {
            'id': self.id,
            'file1Preview': self.file1Preview,
            'file2Preview': self.file2Preview,
            'file3Preview': self.file3Preview,
            'file4Preview': self.file4Preview,
            'file5Preview': self.file5Preview,
            'date_start1': self.date_start1,
            'date_start2': self.date_start2,
            'date_start3': self.date_start3,
            'date_start4': self.date_start4,
            'date_start5': self.date_start5,
            'date_end1': self.date_end1,
            'date_end2': self.date_end2,
            'date_end3': self.date_end3,
            'date_end4': self.date_end4,
            'date_end5': self.date_end5,
            'check1': self.check1,
            'check2': self.check2,
            'check3': self.check3,
            'check4': self.check4,
            'check5': self.check5,
            'rek': self.rek,
            'reko': self.reko
        }


class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    phone_number = db.Column(db.String(20))
    MAC = db.Column(db.String(40), index=True)
    amount = db.Column(db.String(20))
    transaction_id = db.Column(db.String(50))
    state = db.Column(db.String(20))
    status = db.Column(db.String(20))
    account_key = db.Column(db.String(50))
    create_time = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    perform_time = db.Column(db.DateTime)
    cancel_time = db.Column(db.DateTime)
    reason = db.Column(db.String(50))
    link_login = db.Column(db.String(255), nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'phone_number': self.phone_number,
            'amount': self.amount,
            'transaction_id': self.transaction_id,
            'status': self.status,
            'state': self.state,
            'account_key': self.account_key,
            'create_time': self.create_time,
            'perform_time': self.perform_time,
            'cancel_time': self.cancel_time,
            'reason': self.reason, 
            'link_login': self.link_login
        }
