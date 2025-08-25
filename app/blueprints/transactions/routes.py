import datetime
from . import transactions_bp
from sqlalchemy import desc, or_
from flask import jsonify, request
from ...models import Transaction, User
from ...logging_config import configure_logging

logger = configure_logging()


@transactions_bp.route('/api/transactions', methods=['GET'])
def get_transactions():
    try:
        page    = int(request.args.get('page', 1))
        limit   = int(request.args.get('limit', 20))
        sort_by = (request.args.get('sort_by') or 'date').lower()
        sort_dir= (request.args.get('sort_dir') or 'desc').lower()
        reverse = (sort_dir == 'desc')

        def payment_system_from(trans_id: str) -> str:
            if trans_id and trans_id.isdigit():
                return 'Click'
            if trans_id and len(trans_id) == 24:
                try:
                    int(trans_id, 16)
                    return 'PayMe'
                except Exception:
                    pass
            return ''

        def status_rank(s):
            s = (s or '').lower()
            return 3 if s == 'success' else (2 if s == 'pending' else 1)

        # barchasini olib, hisob-kitob qilib keyin saralaymiz
        txs = Transaction.query.all()

        items = []
        for t in txs:
            user = User.query.filter_by(phone_number=t.phone_number).first()
            fio  = user.fio if user else "Unknown"

            if t.status == 'success':
                date_val = t.perform_time or t.create_time
            elif t.status == 'pending':
                date_val = t.create_time
            else:
                date_val = t.cancel_time or t.create_time

            date_str = date_val.strftime("%d-%m-%Y %H:%M:%S") if date_val else "N/A"
            items.append({
                "id":       t.id,
                "fio":      fio,
                "phone":    t.phone_number,
                "amount":   t.amount,            # string/decimal — frontga ko‘rinishi
                "amount_num": float(str(t.amount).replace(' ', '').replace(',', '.')) if t.amount is not None else 0.0,
                "trans_id": t.transaction_id,
                "status":   t.status,
                "date":     date_str,
                "date_sort": date_val or datetime.datetime.min,
                "payment_system": payment_system_from(t.transaction_id),
            })

        # sorting
        def key_func(r):
            if   sort_by == 'id':     return r['id']
            elif sort_by == 'fio':    return (r['fio'] or '').lower()
            elif sort_by == 'phone':  return (r['phone'] or '').lower()
            elif sort_by == 'amount': return r['amount_num']
            elif sort_by in ('payment_system','paymentsystem'): return (r['payment_system'] or '')
            elif sort_by == 'trans_id': return (r['trans_id'] or '')
            elif sort_by == 'status': return status_rank(r['status'])
            elif sort_by == 'date':   return r['date_sort']
            else: return r['date_sort']

        items.sort(key=key_func, reverse=reverse)

        total = len(items)
        start = (page - 1) * limit
        end   = start + limit
        page_items = items[start:end]

        for r in page_items:
            r.pop('amount_num', None)
            r.pop('date_sort', None)

        return jsonify({"transactions": page_items, "total": total}), 200

    except Exception as e:
        logger.error(f"[get_transactions] Error: {e}")
        return jsonify({"error": "Failed to fetch transactions"}), 500
    

@transactions_bp.route('/api/transactions/search', methods=['GET'])
def search_transactions():
    try:
        term = request.args.get('search', default='', type=str).strip().lower()
        logger.info(f"[search_transactions] Search request received: term='{term}'")
        if not term:
            logger.debug("[search_transactions] Empty search term provided, returning empty list")
            return jsonify({"transactions": [], "total": 0}), 200

        pattern = f"%{term}%"
        q = (
            Transaction.query
            .join(User, Transaction.phone_number == User.phone_number)
            .filter(
                or_(
                    Transaction.phone_number.ilike(pattern),
                    Transaction.transaction_id.ilike(pattern),
                    User.fio.ilike(pattern),
                    Transaction.amount.ilike(pattern),
                    Transaction.status.ilike(pattern)
                )
            )
            .order_by(desc(Transaction.create_time))
        )

        total = q.count()
        logger.debug(f"[search_transactions] Found {total} matching records")

        transactions = q.all()
        result = []
        for t in transactions:
            usr = User.query.filter_by(phone_number=t.phone_number).first()
            fio = usr.fio if usr else "Unknown"
            item = {
                "id":       t.id,
                "fio":      fio,
                "phone":    t.phone_number,
                "amount":   t.amount,
                "trans_id": t.transaction_id,
                "status":   t.status,
                "date":     t.create_time.strftime("%d-%m-%Y %H:%M:%S")                             if t.create_time else None
            }
            result.append(item)

        logger.info(f"[search_transactions] Returning {len(result)} items for term='{term}'")
        return jsonify({
            "transactions": result,
            "total":        total
        }), 200

    except Exception as e:
        logger.error(f"[search_transactions] Error: {e}")
        return jsonify({"error": "Search failed"}), 500
