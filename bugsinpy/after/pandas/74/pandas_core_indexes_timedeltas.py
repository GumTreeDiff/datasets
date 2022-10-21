""" implement the TimedeltaIndex """

import numpy as np

from pandas._libs import NaT, Timedelta, index as libindex
from pandas.util._decorators import Appender

from pandas.core.dtypes.common import (
    _TD_DTYPE,
    is_float,
    is_integer,
    is_scalar,
    is_timedelta64_dtype,
    is_timedelta64_ns_dtype,
    pandas_dtype,
)
from pandas.core.dtypes.missing import is_valid_nat_for_dtype

from pandas.core.accessor import delegate_names
from pandas.core.arrays import datetimelike as dtl
from pandas.core.arrays.timedeltas import TimedeltaArray
import pandas.core.common as com
from pandas.core.indexes.base import (
    Index,
    InvalidIndexError,
    _index_shared_docs,
    maybe_extract_name,
)
from pandas.core.indexes.datetimelike import (
    DatetimeIndexOpsMixin,
    DatetimelikeDelegateMixin,
    DatetimeTimedeltaMixin,
)
from pandas.core.indexes.extension import inherit_names

from pandas.tseries.frequencies import to_offset


class TimedeltaDelegateMixin(DatetimelikeDelegateMixin):
    # Most attrs are dispatched via datetimelike_{ops,methods}
    # Some are "raw" methods, the result is not re-boxed in an Index
    # We also have a few "extra" attrs, which may or may not be raw,
    # which we don't want to expose in the .dt accessor.
    _raw_properties = {"components", "_box_func"}
    _raw_methods = {"to_pytimedelta", "sum", "std", "median", "_format_native_types"}

    _delegated_properties = TimedeltaArray._datetimelike_ops + list(_raw_properties)
    _delegated_methods = (
        TimedeltaArray._datetimelike_methods
        + list(_raw_methods)
        + ["_box_values", "__neg__", "__pos__", "__abs__"]
    )


@inherit_names(
    [
        "_bool_ops",
        "_object_ops",
        "_field_ops",
        "_datetimelike_ops",
        "_datetimelike_methods",
        "_other_ops",
    ],
    TimedeltaArray,
)
@delegate_names(
    TimedeltaArray, TimedeltaDelegateMixin._delegated_properties, typ="property"
)
@delegate_names(
    TimedeltaArray,
    TimedeltaDelegateMixin._delegated_methods,
    typ="method",
    overwrite=True,
)
class TimedeltaIndex(
    DatetimeTimedeltaMixin, dtl.TimelikeOps, TimedeltaDelegateMixin,
):
    """
    Immutable ndarray of timedelta64 data, represented internally as int64, and
    which can be boxed to timedelta objects.

    Parameters
    ----------
    data  : array-like (1-dimensional), optional
        Optional timedelta-like data to construct index with.
    unit : unit of the arg (D,h,m,s,ms,us,ns) denote the unit, optional
        Which is an integer/float number.
    freq : str or pandas offset object, optional
        One of pandas date offset strings or corresponding objects. The string
        'infer' can be passed in order to set the frequency of the index as the
        inferred frequency upon creation.
    copy  : bool
        Make a copy of input ndarray.
    name : object
        Name to be stored in the index.

    Attributes
    ----------
    days
    seconds
    microseconds
    nanoseconds
    components
    inferred_freq

    Methods
    -------
    to_pytimedelta
    to_series
    round
    floor
    ceil
    to_frame
    mean

    See Also
    --------
    Index : The base pandas Index type.
    Timedelta : Represents a duration between two dates or times.
    DatetimeIndex : Index of datetime64 data.
    PeriodIndex : Index of Period data.
    timedelta_range : Create a fixed-frequency TimedeltaIndex.

    Notes
    -----
    To learn more about the frequency strings, please see `this link
    <https://pandas.pydata.org/pandas-docs/stable/user_guide/timeseries.html#offset-aliases>`__.
    """

    _typ = "timedeltaindex"

    _engine_type = libindex.TimedeltaEngine

    _comparables = ["name", "freq"]
    _attributes = ["name", "freq"]
    _is_numeric_dtype = True
    _infer_as_myclass = True

    # -------------------------------------------------------------------
    # Constructors

    def __new__(
        cls,
        data=None,
        unit=None,
        freq=None,
        closed=None,
        dtype=_TD_DTYPE,
        copy=False,
        name=None,
    ):
        name = maybe_extract_name(name, data, cls)

        if is_scalar(data):
            raise TypeError(
                f"{cls.__name__}() must be called with a "
                f"collection of some kind, {repr(data)} was passed"
            )

        if unit in {"Y", "y", "M"}:
            raise ValueError(
                "Units 'M' and 'Y' are no longer supported, as they do not "
                "represent unambiguous timedelta values durations."
            )

        if isinstance(data, TimedeltaArray) and freq is None:
            if copy:
                data = data.copy()
            return cls._simple_new(data, name=name, freq=freq)

        if isinstance(data, TimedeltaIndex) and freq is None and name is None:
            if copy:
                return data.copy()
            else:
                return data._shallow_copy()

        # - Cases checked above all return/raise before reaching here - #

        tdarr = TimedeltaArray._from_sequence(
            data, freq=freq, unit=unit, dtype=dtype, copy=copy
        )
        return cls._simple_new(tdarr, name=name)

    @classmethod
    def _simple_new(cls, values, name=None, freq=None, dtype=_TD_DTYPE):
        # `dtype` is passed by _shallow_copy in corner cases, should always
        #  be timedelta64[ns] if present

        if not isinstance(values, TimedeltaArray):
            values = TimedeltaArray._simple_new(values, dtype=dtype, freq=freq)
        else:
            if freq is None:
                freq = values.freq
        assert isinstance(values, TimedeltaArray), type(values)
        assert dtype == _TD_DTYPE, dtype
        assert values.dtype == "m8[ns]", values.dtype

        tdarr = TimedeltaArray._simple_new(values._data, freq=freq)
        result = object.__new__(cls)
        result._data = tdarr
        result._name = name
        # For groupby perf. See note in indexes/base about _index_data
        result._index_data = tdarr._data

        result._reset_identity()
        return result

    # -------------------------------------------------------------------
    # Rendering Methods

    @property
    def _formatter_func(self):
        from pandas.io.formats.format import _get_format_timedelta64

        return _get_format_timedelta64(self, box=True)

    # -------------------------------------------------------------------

    @Appender(_index_shared_docs["astype"])
    def astype(self, dtype, copy=True):
        dtype = pandas_dtype(dtype)
        if is_timedelta64_dtype(dtype) and not is_timedelta64_ns_dtype(dtype):
            # Have to repeat the check for 'timedelta64' (not ns) dtype
            #  so that we can return a numeric index, since pandas will return
            #  a TimedeltaIndex when dtype='timedelta'
            result = self._data.astype(dtype, copy=copy)
            if self.hasnans:
                return Index(result, name=self.name)
            return Index(result.astype("i8"), name=self.name)
        return DatetimeIndexOpsMixin.astype(self, dtype, copy=copy)

    def _maybe_promote(self, other):
        if other.inferred_type == "timedelta":
            other = TimedeltaIndex(other)
        return self, other

    def get_value(self, series, key):
        """
        Fast lookup of value from 1-dimensional ndarray. Only use this if you
        know what you're doing
        """
        if is_integer(key):
            loc = key
        else:
            loc = self.get_loc(key)
        return self._get_values_for_loc(series, loc)

    def get_loc(self, key, method=None, tolerance=None):
        """
        Get integer location for requested label

        Returns
        -------
        loc : int, slice, or ndarray[int]
        """
        if not is_scalar(key):
            raise InvalidIndexError(key)

        if is_valid_nat_for_dtype(key, self.dtype):
            key = NaT

        elif isinstance(key, str):
            try:
                key = Timedelta(key)
            except ValueError:
                raise KeyError(key)

        elif isinstance(key, self._data._recognized_scalars) or key is NaT:
            key = Timedelta(key)

        else:
            raise KeyError(key)

        if tolerance is not None:
            # try converting tolerance now, so errors don't get swallowed by
            # the try/except clauses below
            tolerance = self._convert_tolerance(tolerance, np.asarray(key))

        return Index.get_loc(self, key, method, tolerance)

    def _maybe_cast_slice_bound(self, label, side, kind):
        """
        If label is a string, cast it to timedelta according to resolution.

        Parameters
        ----------
        label : object
        side : {'left', 'right'}
        kind : {'loc', 'getitem'} or None

        Returns
        -------
        label : object
        """
        assert kind in ["loc", "getitem", None]

        if isinstance(label, str):
            parsed = Timedelta(label)
            lbound = parsed.round(parsed.resolution_string)
            if side == "left":
                return lbound
            else:
                return lbound + to_offset(parsed.resolution_string) - Timedelta(1, "ns")
        elif is_integer(label) or is_float(label):
            self._invalid_indexer("slice", label)

        return label

    def _get_string_slice(self, key: str, use_lhs: bool = True, use_rhs: bool = True):
        # TODO: Check for non-True use_lhs/use_rhs
        assert isinstance(key, str), type(key)
        # given a key, try to figure out a location for a partial slice
        raise NotImplementedError

    def is_type_compatible(self, typ) -> bool:
        return typ == self.inferred_type or typ == "timedelta"

    @property
    def inferred_type(self) -> str:
        return "timedelta64"


TimedeltaIndex._add_logical_methods_disabled()


def timedelta_range(
    start=None, end=None, periods=None, freq=None, name=None, closed=None
) -> TimedeltaIndex:
    """
    Return a fixed frequency TimedeltaIndex, with day as the default
    frequency.

    Parameters
    ----------
    start : str or timedelta-like, default None
        Left bound for generating timedeltas.
    end : str or timedelta-like, default None
        Right bound for generating timedeltas.
    periods : int, default None
        Number of periods to generate.
    freq : str or DateOffset, default 'D'
        Frequency strings can have multiples, e.g. '5H'.
    name : str, default None
        Name of the resulting TimedeltaIndex.
    closed : str, default None
        Make the interval closed with respect to the given frequency to
        the 'left', 'right', or both sides (None).

    Returns
    -------
    rng : TimedeltaIndex

    Notes
    -----
    Of the four parameters ``start``, ``end``, ``periods``, and ``freq``,
    exactly three must be specified. If ``freq`` is omitted, the resulting
    ``TimedeltaIndex`` will have ``periods`` linearly spaced elements between
    ``start`` and ``end`` (closed on both sides).

    To learn more about the frequency strings, please see `this link
    <https://pandas.pydata.org/pandas-docs/stable/user_guide/timeseries.html#offset-aliases>`__.

    Examples
    --------

    >>> pd.timedelta_range(start='1 day', periods=4)
    TimedeltaIndex(['1 days', '2 days', '3 days', '4 days'],
                   dtype='timedelta64[ns]', freq='D')

    The ``closed`` parameter specifies which endpoint is included.  The default
    behavior is to include both endpoints.

    >>> pd.timedelta_range(start='1 day', periods=4, closed='right')
    TimedeltaIndex(['2 days', '3 days', '4 days'],
                   dtype='timedelta64[ns]', freq='D')

    The ``freq`` parameter specifies the frequency of the TimedeltaIndex.
    Only fixed frequencies can be passed, non-fixed frequencies such as
    'M' (month end) will raise.

    >>> pd.timedelta_range(start='1 day', end='2 days', freq='6H')
    TimedeltaIndex(['1 days 00:00:00', '1 days 06:00:00', '1 days 12:00:00',
                    '1 days 18:00:00', '2 days 00:00:00'],
                   dtype='timedelta64[ns]', freq='6H')

    Specify ``start``, ``end``, and ``periods``; the frequency is generated
    automatically (linearly spaced).

    >>> pd.timedelta_range(start='1 day', end='5 days', periods=4)
    TimedeltaIndex(['1 days 00:00:00', '2 days 08:00:00', '3 days 16:00:00',
                '5 days 00:00:00'],
               dtype='timedelta64[ns]', freq=None)
    """
    if freq is None and com.any_none(periods, start, end):
        freq = "D"

    freq, freq_infer = dtl.maybe_infer_freq(freq)
    tdarr = TimedeltaArray._generate_range(start, end, periods, freq, closed=closed)
    return TimedeltaIndex._simple_new(tdarr, name=name)
