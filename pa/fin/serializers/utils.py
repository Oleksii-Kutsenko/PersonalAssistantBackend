"""
Mixin for flattening nested object, get from
https://stackoverflow.com/questions/21381700/django-rest-framework-how-do-you-flatten-nested-data
"""


class FlattenMixin:
    """Flatens the specified related objects in this representation"""

    def to_representation(self, obj):
        """
        Overriding default to_representation function for riding nesting
        """
        assert hasattr(self.Meta, 'flatten'), (
            'Class {serializer_class} missing "Meta.flatten" attribute'.format(
                serializer_class=self.__class__.__name__
            )
        )
        # Get the current object representation
        rep = super(FlattenMixin, self).to_representation(obj)
        # Iterate the specified related objects with their serializer
        for field, serializer_class in self.Meta.flatten:
            serializer = serializer_class(context=self.context)
            objrep = serializer.to_representation(getattr(obj, field))
            # Include their fields, prefixed, in the current   representation
            for key in objrep:
                rep[key] = objrep[key]
        return rep
