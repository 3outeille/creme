import csv
import datetime as dt
import os
import random
import typing

from .. import base

from . import utils


__all__ = ['iter_csv']


class DictReader(csv.DictReader):
    """Overlay on top of `csv.DictReader` which allows sampling."""

    def __init__(self, fraction, rng, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fraction = fraction
        self.rng = rng

    def __next__(self):

        if self.line_num == 0:
            self.fieldnames

        row = next(self.reader)

        if self.fraction < 1:
            while self.rng.random() > self.fraction:
                row = next(self.reader)

        return dict(zip(self.fieldnames, row))


def iter_csv(filepath_or_buffer, target_name: str = None, converters: dict = None,
             parse_dates: dict = None, drop: typing.List[str] = None, fraction=1.,
             compression='infer', seed: int = None, field_size_limit: int = None,
             **kwargs) -> base.typing.Stream:
    """Iterates over rows from a CSV file.

    Parameters:
        filepath_or_buffer: Either a string indicating the location of a CSV file, or a buffer
            object that has a ``read`` method.
        target_name: The name of the target.
        converters: A `dict` mapping feature names to callables used to parse their
            associated values.
        parse_dates: A `dict` mapping feature names to a format passed to the
            `datetime.datetime.strptime` method.
        drop: Fields to ignore.
        fraction: Sampling fraction.
        compression: For on-the-fly decompression of on-disk data. If this is set to 'infer' and
            `filepath_or_buffer` is a path, then the decompression method is inferred for the
            following extensions: '.gz', '.zip'.
        seed: If specified, the sampling will be deterministic.
        field_size_limit: If not `None`, this will be passed to the `csv.field_size_limit`
            function.
        kwargs: All other keyword arguments are passed to the underlying `csv.DictReader`.

    Returns:
        By default each feature value will be of type `str`. You can use the `converters` and
        `parse_dates` parameters to convert them as you see fit.

    Example:

        Although this function is designed to handle different kinds of inputs, the most common
        use case is to read a file on the disk. We'll first create a little CSV file to
        illustrate.

        >>> tv_shows = '''name,year,rating
        ... Planet Earth II,2016,9.5
        ... Planet Earth,2006,9.4
        ... Band of Brothers,2001,9.4
        ... Breaking Bad,2008,9.4
        ... Chernobyl,2019,9.4
        ... '''
        >>> with open('tv_shows.csv', mode='w') as f:
        ...     _ = f.write(tv_shows)

        We can now go through the rows one by one. We can use the `converters` parameter to cast
        the `rating` field value as a `float`. We can also convert the `year` to a `datetime` via
        the `parse_dates` parameter.

        >>> from creme import stream

        >>> params = {
        ...     'converters': {'rating': float},
        ...     'parse_dates': {'year': '%Y'}
        ... }
        >>> for x, y in stream.iter_csv('tv_shows.csv', **params):
        ...     print(x, y)
        {'name': 'Planet Earth II', 'year': datetime.datetime(2016, 1, 1, 0, 0), 'rating': 9.5} None
        {'name': 'Planet Earth', 'year': datetime.datetime(2006, 1, 1, 0, 0), 'rating': 9.4} None
        {'name': 'Band of Brothers', 'year': datetime.datetime(2001, 1, 1, 0, 0), 'rating': 9.4} None
        {'name': 'Breaking Bad', 'year': datetime.datetime(2008, 1, 1, 0, 0), 'rating': 9.4} None
        {'name': 'Chernobyl', 'year': datetime.datetime(2019, 1, 1, 0, 0), 'rating': 9.4} None

        The value of ``y`` is always ``None`` because we haven't provided a value for the
        ``target_name`` parameter. Here is an example where a ``target_name`` is provided:

        >>> X_y = stream.iter_csv('tv_shows.csv', target_name='rating', **params)
        >>> for x, y in X_y:
        ...     print(x, y)
        {'name': 'Planet Earth II', 'year': datetime.datetime(2016, 1, 1, 0, 0)} 9.5
        {'name': 'Planet Earth', 'year': datetime.datetime(2006, 1, 1, 0, 0)} 9.4
        {'name': 'Band of Brothers', 'year': datetime.datetime(2001, 1, 1, 0, 0)} 9.4
        {'name': 'Breaking Bad', 'year': datetime.datetime(2008, 1, 1, 0, 0)} 9.4
        {'name': 'Chernobyl', 'year': datetime.datetime(2019, 1, 1, 0, 0)} 9.4

        Finally, let's delete the example file.

        >>> import os; os.remove('tv_shows.csv')

    .. tip::
        Reading CSV files can be quite slow. If, for whatever reason, you're going to loop through
        the same file multiple times, then we recommend that you to use the
        `creme.stream.Cache` utility.

    """

    # Set the field size limit
    limit = csv.field_size_limit()
    if field_size_limit is not None:
        csv.field_size_limit(field_size_limit)

    # If a file is not opened, then we open it
    if not hasattr(filepath_or_buffer, 'read'):
        filepath_or_buffer = utils.open_filepath(filepath_or_buffer, compression)

    for x in DictReader(
        fraction=fraction,
        rng=random.Random(seed),
        f=filepath_or_buffer,
        **kwargs
    ):

        if drop:
            for i in drop:
                del x[i]

        # Cast the values to the given types
        if converters is not None:
            for i, t in converters.items():
                x[i] = t(x[i])

        # Parse the dates
        if parse_dates is not None:
            for i, fmt in parse_dates.items():
                x[i] = dt.datetime.strptime(x[i], fmt)

        # Separate the target from the features
        y = x.pop(target_name, None)

        yield x, y

    # Close the file
    filepath_or_buffer.close()

    # Reset the file size limit to it's original value
    csv.field_size_limit(limit)
