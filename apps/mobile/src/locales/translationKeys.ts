import enGB from './en-GB.json';

type Primitive = string | number | boolean | null | undefined;

type NestedKeys<T> = T extends Primitive
  ? never
  : {
      [K in keyof T & string]: T[K] extends Primitive
        ? K
        : `${K}.${NestedKeys<T[K]>}`;
    }[keyof T & string];

export type TranslationKey = NestedKeys<typeof enGB>;
