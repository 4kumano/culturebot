"""General iterator and asyncio tools"""
from __future__ import annotations

import asyncio
from asyncio.events import AbstractEventLoop
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from itertools import repeat
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
def asyncify(func: Callable[P, T]) -> Callable[P, Coroutine[Any, Any, T]]:
    """Turn a normal function into a coroutine.
    We don't use an awaitable because of type restrictions in dpy"""
    loop = asyncio.get_event_loop()
    async def wrapper(*args, **kwargs):
        return await loop.run_in_executor(async_executor, partial(func, *args, **kwargs))
    return wrapper

async def to_async_iterator(iterable: Union[Iterable[T]], loop: AbstractEventLoop = None) -> AsyncIterator[T]:
    """Turns an iterator into an async iterator"""
    def _next(iterator):
        try:
            return next(iterator)
        except StopIteration:
            return None
    
    loop = loop or asyncio.get_event_loop()
    it = iter(iterable)
    while True:
        x = await loop.run_in_executor(async_executor, _next, it)
        if x is None:
            return
        yield x

def to_sync_iterator(iterable: Union[AsyncIterable[T]], loop: AbstractEventLoop = None) -> Iterator[T]:
    """Turns an async iterator into an iterator"""
    loop = loop or asyncio.get_event_loop()
    it = iterable.__aiter__()
    while True:
        try:
            task = asyncio.run_coroutine_threadsafe(it.__anext__(), loop=loop)
            while not task.done():
                print('waiting for',task)
            yield task.result()
        except StopAsyncIteration:
            return

def repeat_once(first: T1, rest: T2 = '\u200b') -> Iterator[Union[T1, T2]]:
    yield first
    yield from repeat(rest)

def zip_once(iterable: Iterable[T], first: T1, rest: T2 = '\u200b') -> Iterator[tuple[T, Union[T1, T2]]]:
    yield from zip(iterable, repeat_once(first, rest))



class bicycle(Iterator[T]):
    """A cycle that supports getting previous values"""
    it: Iterator[T]
    saved: list[T]
    index: int = 0
    depleted: bool = False 
    
    def __init__(self, iterable: Iterable[T]):
        self.it = iter(iterable)
        self.saved = []
    
    def __repr__(self) -> str:
        return f"<{type(self).__name__} index={self.index} depleted={self.depleted} saved={self.saved}>"

    @property
    def curr(self) -> T:
        if self.depleted:
            self.index %= len(self.saved)
        elif self.index < 0:
            raise IndexError
        
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
    
    __next__ = next
