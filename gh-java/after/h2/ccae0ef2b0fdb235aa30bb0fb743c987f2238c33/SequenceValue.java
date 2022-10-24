/*
 * Copyright 2004-2006 H2 Group. Licensed under the H2 License, Version 1.0 (http://h2database.com/html/license.html).
 * Initial Developer: H2 Group
 */
package org.h2.expression;

import java.sql.SQLException;

import org.h2.engine.Session;
import org.h2.message.Message;
import org.h2.schema.Sequence;
import org.h2.table.ColumnResolver;
import org.h2.table.TableFilter;
import org.h2.value.Value;
import org.h2.value.ValueInt;
import org.h2.value.ValueLong;

public class SequenceValue extends Expression {

    private Sequence sequence;

    public SequenceValue(Sequence sequence) {
        this.sequence = sequence;
    }

    public Value getValue(Session session) throws SQLException {
        long value = sequence.getNext();
        session.setLastIdentity(value);
        return ValueLong.get(value);
    }

    public int getType() {
        return Value.LONG;
    }

    public void mapColumns(ColumnResolver resolver, int level) {
        // nothing to do
    }

    public void checkMapped() {
        // nothing to do
    }

    public Expression optimize(Session session) {
        return this;
    }

    public void setEvaluatable(TableFilter tableFilter, boolean b) {
        // nothing to do
    }

    public int getScale() {
        return 0;
    }

    public long getPrecision() {
        return ValueInt.PRECISION;
    }

    public String getSQL() {
        return "(NEXT VALUE FOR " + sequence.getSQL() +")";
    }

    public void updateAggregate(Session session) {
        // nothing to do
    }

    public boolean isEverything(ExpressionVisitor visitor) {
        switch(visitor.type) {
        case ExpressionVisitor.OPTIMIZABLE_MIN_MAX_COUNT_ALL:
            return true;
        case ExpressionVisitor.DETERMINISTIC:
        case ExpressionVisitor.READONLY:
            return false;
        case ExpressionVisitor.INDEPENDENT:
            return false;
        case ExpressionVisitor.EVALUATABLE:
            return true;
        case ExpressionVisitor.SET_MAX_DATA_MODIFICATION_ID:
            visitor.addDataModificationId(sequence.getModificationId());
            return true;
        default:
            throw Message.getInternalError("type="+visitor.type);
        }
    }
    
    public int getCost() {
        return 1;
    }
    
}
