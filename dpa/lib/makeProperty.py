from types import ClassType, TypeType, NoneType
import sys

def makeProperty(*acceptable_types):

  typeList = []
  hasNone = False
  for typ in acceptable_types:
    if typ is None or typ == NoneType:
      hasNone = True
    elif type(typ) not in (ClassType, TypeType):
      raise TypeError, "'%s' is not class or type" % typ
    else:
      typeList.append(typ)
  if not typeList:
    if hasNone:
      raise TypeError, "no reason store only None value in property"
  else:
    if len(typeList) == 1:
      badTypeMsg = "value must be %s instance" % typeList[0].__name__
    else:
      badTypeMsg = ', '.join(['%s' % x.__name__ for x in typeList])
      badTypeMsg = "value must be instance of one of (%s) types" % badTypeMsg
    if hasNone:
      badTypeMsg = "%s or None" % badTypeMsg
    typeList.append(NoneType)
  typeList = tuple(typeList)

  def property_maker(function):
    func_attr_names = ('fget', 'fset', 'fdel', 'name', 'prepare')
    func_attrs = {}

    f_code_name = function.func_code.co_name
    def probeFunc(frame, event, arg):
      if event == 'return' and frame.f_code.co_name == f_code_name:
        frLocals = frame.f_locals
        for name in func_attr_names:
          try:
            func_attrs[name] = frLocals[name]
          except:
            pass
        sys.settrace(None)
      return probeFunc
    sys.settrace(probeFunc)
    function()

    msg = "'%s' must be callable or None"
    try:
      name = func_attrs['name']
    except:
      name = '_%s_property_value' % function.__name__
    else:
      if not isinstance(name, str):
        raise TypeError, "'name' must be string or None"
    try:
      prepare = func_attrs['prepare']
    except:
      prepare = None
    else:
      if not callable(prepare) and prepare is not None:
        raise TypeError, msg % 'prepare'

    def fget_default(self):
      return getattr(self, name)

    def fset_default(self, value):
      if prepare is not None:
        value = prepare(self, value)
      setattr(self, name, value)

    def fdel_default(self):
      delattr(self, name)

    try:
      fget = func_attrs['fget']
    except:
      fget = fget_default
    else:
      if not callable(fget) and fget is not None:
        raise TypeError, msg % 'fget'
    try:
      fset = func_attrs['fset']
    except:
      fset = fset_default
    else:
      if not callable(fset) and fset is not None:
        raise TypeError, msg % 'fset'
    try:
      fdel = func_attrs['fdel']
    except:
      fdel = fdel_default
    else:
      if not callable(fdel) and fdel is not None:
        raise TypeError, msg % 'fdel'
    fdoc = function.__doc__
    if not isinstance(fdoc, basestring) and fdoc is not None:
      raise TypeError, "'fdoc' must be string, unicode or None"

    if acceptable_types and fset is not None:
      def wrapped_fset(self, value):
        if isinstance(value, typeList):
          return fset(self, value)
        else:
          raise TypeError, badTypeMsg
      return property(fget, wrapped_fset, fdel, fdoc)
    else:
      return property(fget, fset, fdel, fdoc)
  return property_maker