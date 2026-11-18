"""Pure helpers for editing nested block scripts.

A *path* is a tuple of ``(slot_name, block_index)`` pairs leading from a
script's top-level block list into a nested C-slot.  A *location* combines a
script index, a path, and an item index: ``(script_index, path, index)``.
"""

from core import BLOCKS, block


def blocks_at(project, script_index):
    """Return the top-level block list for a script or procedure.

    Scripts use non-negative indexes into ``project.scripts``.  Procedures use
    negative indexes, with ``-1`` meaning the first procedure, so the existing
    nested-editing helpers work for custom block bodies without a second API.
    """
    if script_index >= 0:
        if script_index >= len(project.scripts):
            raise ValueError("script index %r is out of range" % script_index)
        return project.scripts[script_index]["blocks"]
    procedure_index = -1 - script_index
    if procedure_index >= len(project.procedures):
        raise ValueError("procedure index %r is out of range" % procedure_index)
    return project.procedures[procedure_index].blocks


def container(project, script_index, path=()):
    """Return the block list addressed by *script_index* and *path*."""
    return _items_at(project, (script_index, path, 0), check_index=False)


def _items_at(project, location, check_index=True, allow_end=False):
    script_index, path, index = location
    items = blocks_at(project, script_index)
    for slot, block_index in path:
        if not 0 <= block_index < len(items):
            raise ValueError("block index %r is out of range" % (block_index,))
        items = items[block_index].children[slot]
    if check_index and not 0 <= index < len(items) + (1 if allow_end else 0):
        raise ValueError("item index %r is out of range" % (index,))
    return items


def _adjust_path(path, source_path, source_index):
    """Translate a target path to the list after the source block is removed."""
    if len(path) <= len(source_path) or path[:len(source_path)] != source_path:
        return path
    slot, block_index = path[len(source_path)]
    if block_index == source_index:
        raise ValueError("cannot move a block into its own child slot")
    if block_index > source_index:
        return (path[:len(source_path)] +
                ((slot, block_index - 1),) +
                path[len(source_path) + 1:])
    return path


def insert_block(project, script_index, path, index, type_):
    """Insert a fresh block of *type_* into a script and return it."""
    definition = BLOCKS.get(type_)
    if definition is None:
        raise KeyError(type_)
    item = block(type_, children={slot: [] for slot in definition.slots})
    items = _items_at(project, (script_index, path, index), check_index=False)
    items.insert(max(0, min(index, len(items))), item)
    return item


def remove_block(project, script_index, path, index):
    """Remove and return the block at ``(script_index, path, index)``."""
    return _items_at(project, (script_index, path, index)).pop(index)


def move_block(project, source, target):
    """Move one block between locations.

    The target index is the block's index in the final list, which makes drag
    and drop behave the same way within a stack and between scripts.  Target
    paths that point past the removed block are shifted to the new positions.
    """
    source_script, source_path, source_index = source
    target_script, target_path, target_index = target
    source_items = _items_at(project, source)
    _items_at(project, target, allow_end=True)
    if source_script == target_script:
        target_path = _adjust_path(target_path, source_path, source_index)
    item = source_items.pop(source_index)
    items = _items_at(project, (target_script, target_path, target_index),
                      allow_end=True)
    items.insert(max(0, min(target_index, len(items))), item)
    return item
