from typing import Iterable, Iterator, TypeVar

T = TypeVar('T')

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

if __name__ == '__main__':
    from pprint import pprint
    it = bicycle([1,2,3,4,5])
    print(it.curr)
    print(it.prev())
    print(it.next(), it)
    print(it.prev(), it)
    print(next(it), it)
    for _ in range(6):
        print('', it.next(), it)
    for _ in range(10):
        print(it.prev(), it)