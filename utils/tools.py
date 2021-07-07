"""General iterator and asyncio tools"""
from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from itertools import repeat
import inspect
from typing import *  # type: ignore

if TYPE_CHECKING: # 3.10 is not out yet techincally
    from typing_extensions import ParamSpec
else:
    ParamSpec = lambda *_,**__: None

T = TypeVar("T")
T1 = TypeVar("T1")
T2 = TypeVar("T2")
P = ParamSpec("P")

async_executor = ThreadPoolExecutor(max_workers=32)
def to_thread(func: Callable[..., T], *args, **kwargs) -> Awaitable[T]:
    """Like asyncio.to_thread() but <3.9 and uses the a custom executor"""
    loop = asyncio.get_event_loop()
    return loop.run_in_executor(async_executor, partial(func, *args, **kwargs))

def coroutine(func: Callable[P, T]) -> Callable[P, Coroutine[Any, Any, T]]:
    """Turn a normal function into a coroutine."""
    if inspect.iscoroutinefunction(func):
        raise TypeError("Cannot turn a coroutine into a coroutine")
    
    async def wrapper(*args, **kwargs):
        return await to_thread(func, *args, **kwargs)
    return wrapper

async def maybe_anext(it: Union[Iterator[T], AsyncIterator[T]], default: Any = ...) -> T:
    try:
        if isinstance(it, Iterator):
            return next(it)
        else:
            return await it.__anext__()
    except (StopIteration, StopAsyncIteration):
        if default is ...:
            raise
        return default

async def to_async_iterator(iterable: Iterable[T], loop: asyncio.AbstractEventLoop = None) -> AsyncIterator[T]:
    """Turns an iterator into an async iterator"""
    loop = loop or asyncio.get_event_loop()
    it = iter(iterable)
    while True:
        x: Optional[T] = await loop.run_in_executor(async_executor, next, it, None) # type: ignore
        if x is None:
            return
        yield x

def to_sync_iterator(iterable: AsyncIterable[T]) -> Iterator[T]:
    """Turns an async iterator into an iterator
    
    There are some limitations to this function, mainly with futures
    so use only when absolutely neccessary.
    """
    it = iterable.__aiter__()
    while True:
        try:
            yield (yield from it.__anext__().__await__())
        except StopAsyncIteration:
            return

def repeat_once(first: T1, rest: T2 = '\u200b') -> Iterator[Union[T1, T2]]:
    yield first
    yield from repeat(rest)

def zip_once(iterable: Iterable[T], first: T1, rest: T2 = '\u200b') -> Iterator[tuple[T, Union[T1, T2]]]:
    yield from zip(iterable, repeat_once(first, rest))


class Zipper(Iterator[T]):
    """A cycle that supports getting previous values with (partial) async support."""
    it: Iterator[T]
    saved: list[T]
    index: int = 0
    depleted: bool = False 
    
    def __init__(self, iterable: Union[Iterable[T], AsyncIterable[T]]):
        if isinstance(iterable, Sequence):
            self.it = iter(())
            self.saved = list(iterable)
        elif isinstance(iterable, Iterable):
            self.it = iter(iterable)
            self.saved = []
        else:
            self.it = to_sync_iterator(iterable)
            self.saved = []
    
    def __repr__(self) -> str:
        return f"<{type(self).__name__} index={self.index} depleted={self.depleted} saved={self.saved}>"

    @property
    def curr(self) -> T:
        if self.depleted:
            self.index %= len(self.saved)
        elif self.index < 0:
            self.index = 0
            raise IndexError("Cannot get the last item of an undepleted zipper")
        
        if self.index < len(self.saved):
            return self.saved[self.index]
        
        value = next(self.it, None)
        if value is None:
            self.depleted = True
            return self.curr
        
        self.saved.append(value)
        return value
    
    def next(self) -> T:
        self.index += 1
        return self.curr
    
    def prev(self) -> T:
        self.index -= 1
        return self.curr
    
    anext = coroutine(next)
    aprev = coroutine(prev)
    __next__ = next
    __anext__ = anext
